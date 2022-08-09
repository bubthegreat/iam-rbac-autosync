import yaml
import pytest
from src.handlers.handler import get_updated_map_users

def _add_iam_groups(iam_client):
    iam_client.create_group(GroupName="eks-empty")
    iam_client.create_group(GroupName="eks-devops")
    iam_client.create_group(GroupName="eks-developers")
    iam_client.create_group(GroupName="eks-zeus-elevated")
    iam_client.create_group(GroupName="eks-console-elevated")

    iam_client.create_user(UserName="eks-admin-1")
    iam_client.create_user(UserName="eks-admin-2")
    iam_client.create_user(UserName="user1")
    iam_client.create_user(UserName="user2")
    iam_client.create_user(UserName="user3")

    iam_client.add_user_to_group(GroupName="eks-devops", UserName="eks-admin-1")
    iam_client.add_user_to_group(GroupName="eks-devops", UserName="eks-admin-2")
    iam_client.add_user_to_group(GroupName="eks-developers", UserName="eks-admin-1")
    iam_client.add_user_to_group(GroupName="eks-developers", UserName="eks-admin-2")
    iam_client.add_user_to_group(GroupName="eks-developers", UserName="user1")
    iam_client.add_user_to_group(GroupName="eks-developers", UserName="user2")
    iam_client.add_user_to_group(GroupName="eks-developers", UserName="user3")
    iam_client.add_user_to_group(GroupName="eks-zeus-elevated", UserName="user1")
    iam_client.add_user_to_group(GroupName="eks-console-elevated", UserName="user2")
    iam_client.add_user_to_group(GroupName="eks-console-elevated", UserName="user3")

    return iam_client


@pytest.mark.parametrize('rbac_mapper_yaml_file, aws_auth_configmap_yaml_file', [
    ('dev-iam-rbac-autosync.yaml', 'dev-aws-auth-configmap.yaml'),
    ('prod-iam-rbac-autosync.yaml', 'prod-aws-auth-configmap.yaml'),
])
def test_get_updated_map_users(mocker, iam_client, rbac_mapper_yaml_file, aws_auth_configmap_yaml_file):

    # We don't want to create any bound elevated namespaces - we need to fake the k8s calls.
    mocker.patch(
        'src.handlers.handler.create_bound_elevated_namespace',
        return_value = True
    )
    client = _add_iam_groups(iam_client)   
    
    # Open our files that represent "processed" data that we know is good
    with open(f'tests/fixtures/{rbac_mapper_yaml_file}', "r") as stream:
        rbac_mapper = yaml.safe_load(stream)

    with open(f'tests/fixtures/{aws_auth_configmap_yaml_file}', "r") as stream:
        aws_auth_configmap = yaml.safe_load(stream)
    
    # Compare the results to make sure we don't break something without a test catching it.
    spec = rbac_mapper['spec']
    updated_map_users = get_updated_map_users(spec)
    assert aws_auth_configmap['data']['mapUsers'] == updated_map_users