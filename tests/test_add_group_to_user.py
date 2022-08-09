import pytest
import boto3
import os

from moto import mock_iam



from src.handlers.handler import add_group_to_user

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


@pytest.mark.parametrize("username, groupname, expected",[
    ('eks-admin-1', 'system:masters', {'system:masters'}),
    ('user1', 'admin', {'admin'}),
    ('user2', 'view', {'view'}),
    ('user3', 'eks-zeus-elevated', {'eks-zeus-elevated'}),
])
def test_add_group_to_user(iam_client, username, groupname, expected):

    client = _add_iam_groups(iam_client)

    users_dict = {}
    user = client.get_user(UserName=username)
    add_group_to_user(users_dict, user['User'], groupname)
    assert users_dict[username]['"groups"'] == expected


@pytest.mark.parametrize("username, groupname, exception",[
    ('user1', '', ValueError),
])
def test_errors_add_group_to_user(users_dict, iam_client, username, groupname, exception):
    client = _add_iam_groups(iam_client)
    user = client.get_user(UserName=username)
    with pytest.raises(exception):
        add_group_to_user(users_dict, user['User'], groupname)


@pytest.mark.parametrize("username, groups, result",[
    ('eks-admin-1', ['system:masters', 'view'], {'system:masters', 'view'}),    # normal
    ('eks-admin-2', ['system:masters', 'view'], {'system:masters', 'view'}),    # different user
    ('user1', ['admin'], {'admin'}),                                            # different group
    ('user1', ['admin', 'eks-zeus-elevated'], {'admin', 'eks-zeus-elevated'}),  # Multi group
])
def test_multi_add_group_to_user(users_dict, iam_client, username, groups, result):  
    client = _add_iam_groups(iam_client)
    user = client.get_user(UserName=username)
    for groupname in groups:
        add_group_to_user(users_dict, user['User'], groupname)
    assert users_dict[username]['"groups"'] == result
    return users_dict
