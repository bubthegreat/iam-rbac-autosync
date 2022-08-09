import pytest

from src.handlers.handler import get_or_create_iam_group


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

@pytest.mark.parametrize("group_name, members",[
    ('eks-non-existent', 0),
    ('eks-empty', 0),
    ('eks-devops', 2),
    ('eks-developers', 5),
    ('eks-zeus-elevated', 1),
    ('eks-console-elevated', 2),
])
def test_get_or_create_iam_group(iam_client, group_name, members):   
    client = _add_iam_groups(iam_client)   
    group = get_or_create_iam_group(group_name)
    
    assert len(group.get('Users', [])) == members
