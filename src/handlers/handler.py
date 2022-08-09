""" Hooray, an operator that keeps our IAM and RBAC groups in sync!!

Ideally this will serve our purposes, however if you need ABAC this won't be
able to meet your needs.  For ABAC we will need to put together a tagging
strategy that we can programmatically apply and check.



"""

import kopf
import logging
import boto3  # type: ignore
import kubernetes  # type: ignore
import copy
import os
import yaml  # type: ignore
from typing import Dict, Any, List
from kubernetes.client.rest import ApiException  # type: ignore


CRD_HANDLER_NAME = "iam-rbac-autosyncs"
LOGGER_NAME = f"{CRD_HANDLER_NAME}-logger"

LOGGER = logging.getLogger(LOGGER_NAME)

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")


@kopf.timer(CRD_HANDLER_NAME, interval=30.0)
def update_rbac_with_iam_changes(body, **kwargs):
    current_auth_configmap = get_current_configmap("aws-auth", "kube-system")
    updated_auth_configmap = get_updated_configmap(current_auth_configmap, body["spec"])
    update_configmap(current_auth_configmap, updated_auth_configmap)


class NoAliasDumper(yaml.SafeDumper):
    """Prevent aliases from being used in yaml for multi-referenced keys."""

    def ignore_aliases(self, data: Any) -> bool:
        """Pass through aliases."""
        return True


def get_or_create_iam_group(group_name):
    """Get or create the IAM group required by the objects."""
    # TODO: How should cleanup for this be handled?  Should we ever clean this up?
    client = boto3.client(
        "iam", aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_ACCESS_KEY
    )
    try:
        group = client.get_group(GroupName=group_name)
        LOGGER.info("IAM group %s found.", group_name)
    except client.exceptions.NoSuchEntityException:
        LOGGER.info("IAM group %s does not exist", group_name)
        group = client.create_group(GroupName=group_name)
        LOGGER.info("IAM group created %s.", group_name)

    # TODO: Find a way to self reference the cluster information so that we can
    #       auto-add the correct IAM permissions to the correct group, i.e.
    #       eks-developers should all get access to the dev cluster, but not the
    #       prod
    return group


def get_group_users(group_name: str) -> List[Dict[str, Any]]:
    """Return iam dict objects representing users for a given group."""
    groupdict = get_or_create_iam_group(group_name)
    users = [u for u in groupdict.get("Users", [])]
    return users


def add_group_to_user(
    users_dict: Dict[str, Any], iam_user: Dict[str, Any], group: str
) -> None:
    """Adds a group to a user object and creates a user object if it doesn't already exist."""
    if not group or type(group) != str:
        raise ValueError(f"Group must be a non-empty string but got: {group}.")

    username = iam_user["UserName"]

    # Make sure there's a user object in this dict.
    if not users_dict.get(username):
        LOGGER.debug("User not found in user dict for %s", username)
        userdict: Dict[str, Any] = {}
        userdict['"groups"'] = set()
        userdict['"userarn"'] = f'"{iam_user["Arn"]}"'
        userdict['"username"'] = f'"{username}"'
        users_dict[username] = userdict

    users_dict[username]['"groups"'].add(group)


def get_updated_map_users(spec: Dict[str, Any]) -> str:
    """Create an updated list of users for the configmap."""
    users: Dict[str, Any] = {}

    for group_name in spec["clusterAdminGroups"]:
        for user in get_group_users(group_name):
            add_group_to_user(users, user, '"system:masters"')

    for group_name in spec["eksAdminGroups"]:
        for user in get_group_users(group_name):
            add_group_to_user(users, user, '"admin"')

    for group_name in spec["viewGroups"]:
        for user in get_group_users(group_name):
            add_group_to_user(users, user, '"view"')

    for ns_elevated_info in spec.get("namespaceElevatedGroups", []):
        for group_name in ns_elevated_info["elevatedGroups"]:
            create_bound_elevated_namespace(
                ns_elevated_info["protectedNameSpace"], group_name
            )
            for user in get_group_users(group_name):
                add_group_to_user(users, user, f'"{group_name}"')
    for key, value in users.items():
        value['"groups"'] = sorted(
            list(value['"groups"'])
        )  # We're sorting these so there's a consistent order, but it's really just for testing.
        LOGGER.debug("updated groups to list for %s", key)

    updated = [users[key] for key in sorted(users.keys())]
    updated_map_users = yaml.dump(updated, Dumper=NoAliasDumper).replace(
        "'", ""
    )  # Lots of weird escaping, there's gotta be a better way to get the right yaml.
    return updated_map_users


def get_updated_configmap(aws_auth_configmap, spec):
    """Create an updated configmap for the given admin and elevated groups."""
    updated_aws_auth_configmap = copy.deepcopy(aws_auth_configmap)
    updated_aws_auth_configmap.data["mapUsers"] = get_updated_map_users(spec)
    return updated_aws_auth_configmap


def update_configmap(current_auth_configmap, updated_auth_configmap):
    """Update the existing aws-auth configmap with an updated configmap."""
    result = None
    old_map_users_set = sorted(current_auth_configmap.data["mapUsers"].splitlines())
    new_map_users_set = sorted(updated_auth_configmap.data["mapUsers"].splitlines())

    user_changes = old_map_users_set != new_map_users_set
    if user_changes:
        LOGGER.info("Changes detected in group membership")
        k8s_client = kubernetes.client.ApiClient()
        api_instance = kubernetes.client.CoreV1Api(k8s_client)
        api_response = api_instance.patch_namespaced_config_map(
            "aws-auth", "kube-system", updated_auth_configmap, pretty=True
        )
        result = api_response
    else:
        LOGGER.info("No changes detected in group membership")

    return result


def get_current_configmap(
    configmap_name: Any, namespace: str, pretty: bool = True
) -> Any:
    """Get the current configmap object for aws-auth."""
    k8s_client = kubernetes.client.ApiClient()
    api_instance = kubernetes.client.CoreV1Api(k8s_client)
    current_auth_configmap = api_instance.read_namespaced_config_map(
        configmap_name, namespace, pretty=True
    )
    return current_auth_configmap


def _get_iam_rbac_spec(iam_rbac_name: str):
    """Get the IAM RBAC CRD spec and return it."""
    # Used for iteration where the body may not be available for the kopf crd.
    k8s_client = kubernetes.client.ApiClient()
    api_instance = kubernetes.client.CustomObjectsApi(k8s_client)
    api_response = api_instance.get_cluster_custom_object(
        "iamrbacautoupdater.com", "v1", "iam-rbac-autosyncs", iam_rbac_name
    )
    return api_response["spec"]


def create_admin_binding(namespace, eks_group):
    """Create a role binding for the namespace to its eks group."""
    namespaced_role_name = f"{namespace}-elevated"
    api = kubernetes.client.RbacAuthorizationV1Api(kubernetes.client.ApiClient())

    try:
        api_response = api.read_namespaced_role_binding(namespaced_role_name, namespace)
        LOGGER.debug(
            "Found namespace %s binding %s for group %s",
            namespace,
            namespaced_role_name,
            eks_group,
        )

    except ApiException:

        body = kubernetes.client.V1RoleBinding(
            api_version="rbac.authorization.k8s.io/v1",
            kind="RoleBinding",
            metadata=kubernetes.client.V1ObjectMeta(
                name=namespaced_role_name,
                namespace=namespace,
            ),
            subjects=[
                kubernetes.client.V1Subject(
                    kind="Group",
                    name=eks_group,
                    api_group="rbac.authorization.k8s.io",
                ),
            ],
            role_ref=kubernetes.client.V1RoleRef(
                kind="Role",
                name="admin",
                api_group="rbac.authorization.k8s.io",
            ),
        )
        LOGGER.debug(
            "admin binding %s in namespace %s not found for group %s - attempting to create namespace binding",
            namespaced_role_name,
            namespace,
            eks_group,
        )
        api_response = api.create_namespaced_role_binding(namespace, body)
        LOGGER.debug(
            "Created %s role binding %s for group %s",
            namespace,
            namespaced_role_name,
            eks_group,
        )
    return api_response


def create_elevated_namespace(namespace_name):
    """Create a namespace for elevated RBAC required access."""
    api = kubernetes.client.CoreV1Api(kubernetes.client.ApiClient())

    try:
        namespace_obj = api.read_namespace(name=namespace_name)
        LOGGER.info("Namespace already exists: %s", namespace_name)

    except ApiException:
        LOGGER.info("Namespace not found: %s", namespace_name)

        body = kubernetes.client.V1Namespace(
            api_version="v1",
            kind="Namespace",
            metadata=kubernetes.client.V1ObjectMeta(
                name=namespace_name,
            ),
        )
        LOGGER.debug("Attempting to create namespace %s", namespace_name)
        namespace_obj = api.create_namespace(body)

    return namespace_obj


def create_bound_elevated_namespace(namespace_name, eks_group):
    """Create an elevated namespace and bind the RBAC permission to it."""
    ns_resp = create_elevated_namespace(namespace_name)
    bind_resp = create_admin_binding(namespace_name, eks_group)
    return ns_resp, bind_resp
