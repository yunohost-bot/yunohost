import pytest

from moulinette.core import MoulinetteError
from yunohost.user import user_list, user_info, user_create, user_delete, user_update, \
                          user_group_list, user_group_create, user_group_delete, user_group_update, user_group_info
from yunohost.domain import _get_maindomain
from yunohost.utils.error import YunohostError
from yunohost.tests.test_permission import check_LDAP_db_integrity

# Get main domain
maindomain = _get_maindomain()

def clean_user_groups():
    for u in user_list()['users']:
        user_delete(u)

    for g in user_group_list()['groups']:
        if g != "all_users":
            user_group_delete(g)

def setup_function(function):
    clean_user_groups()

    user_create("alice", "Alice", "White", "alice@" + maindomain, "test123Ynh")
    user_create("bob", "Bob", "Snow", "bob@" + maindomain, "test123Ynh")
    user_create("jack", "Jack", "Black", "jack@" + maindomain, "test123Ynh")

    user_group_create("dev")
    user_group_create("apps")
    user_group_update("dev", add=["alice"])
    user_group_update("apps", add=["bob"])

def teardown_function(function):
    clean_user_groups()

@pytest.fixture(autouse=True)
def check_LDAP_db_integrity_call():
    check_LDAP_db_integrity()
    yield
    check_LDAP_db_integrity()

#
# List functions
#

def test_list_users():
    res = user_list()['users']

    assert "alice" in res
    assert "bob" in res
    assert "jack" in res

def test_list_groups():
    res = user_group_list()['groups']

    assert "all_users" in res
    assert "alice" in res
    assert "bob" in res
    assert "jack" in res
    for u in ["alice", "bob", "jack"]:
        assert u in res
        assert u in res[u]['members']
        assert u in res["all_users"]['members']

#
# Create - Remove functions
#

def test_create_user():
    user_create("albert", "Albert", "Good", "alber@" + maindomain, "test123Ynh")

    group_res = user_group_list()['groups']
    assert "albert" in user_list()['users']
    assert "albert" in group_res
    assert "albert" in group_res['albert']['members']
    assert "albert" in group_res['all_users']['members']

def test_del_user():
    user_delete("alice")

    group_res = user_group_list()['groups']
    assert "alice" not in user_list()
    assert "alice" not in group_res
    assert "alice" not in group_res['all_users']['members']

def test_create_group():
    user_group_create("adminsys")

    group_res = user_group_list()['groups']
    assert "adminsys" in group_res
    assert "members" in group_res['adminsys'].keys()
    assert group_res["adminsys"]["members"] == []

def test_del_group():
    user_group_delete("dev")

    group_res = user_group_list()['groups']
    assert "dev" not in group_res

#
# Error on create / remove function
#

def test_create_user_with_mail_address_already_taken():
    with pytest.raises(MoulinetteError):
        user_create("alice2", "Alice", "White", "alice@" + maindomain, "test123Ynh")

def test_create_user_with_password_too_simple():
    with pytest.raises(MoulinetteError):
        user_create("other", "Alice", "White", "other@" + maindomain, "12")

def test_create_user_already_exists():
    with pytest.raises(MoulinetteError):
        user_create("alice", "Alice", "White", "other@" + maindomain, "test123Ynh")

def test_del_user_that_does_not_exist():
    with pytest.raises(MoulinetteError):
        user_delete("doesnt_exist")

def test_create_group_all_users():
    # Check groups already exist with special group "all_users"
    with pytest.raises(YunohostError):
        user_group_create("all_users")

def test_create_group_already_exists():
    # Check groups already exist (regular groups)
    with pytest.raises(MoulinetteError):
        user_group_create("dev")

def test_del_group_all_users():
    with pytest.raises(YunohostError):
        user_group_delete("all_users")

def test_del_group_that_does_not_exist():
    with pytest.raises(MoulinetteError):
        user_group_delete("doesnt_exist")

#
# Update function
#

def test_update_user():
    user_update("alice", firstname="NewName", lastname="NewLast")

    info = user_info("alice")
    assert info['firstname'] == "NewName"
    assert info['lastname'] == "NewLast"

def test_update_group_add_user():
    user_group_update("dev", add=["bob"])

    group_res = user_group_list()['groups']
    assert set(group_res['dev']['members']) == set(["alice", "bob"])

def test_update_group_add_user_already_in():
    user_group_update("apps", add=["bob"])

    group_res = user_group_list()['groups']
    assert group_res['apps']['members'] == ["bob"]

def test_update_group_remove_user():
    user_group_update("apps", remove=["bob"])

    group_res = user_group_list()['groups']
    assert group_res['apps']['members'] == []

def test_update_group_remove_user_not_already_in():
    user_group_update("apps", remove=["jack"])

    group_res = user_group_list()['groups']
    assert group_res['apps']['members'] == ["bob"]

#
# Error on update functions
#

def test_update_user_that_doesnt_exist():
    with pytest.raises(YunohostError):
        user_update("doesnt_exist", firstname="NewName", lastname="NewLast")

def test_update_group_that_doesnt_exist():
    # Check groups not found
    with pytest.raises(YunohostError):
        user_group_update("doesnt_exist", add=["alice"])

def test_update_group_all_users_manually():
    with pytest.raises(YunohostError):
        user_group_update("all_users", remove=["alice"])

    assert "alice" in user_group_list()["groups"]["all_users"]["members"]

def test_update_group_primary_manually():
    with pytest.raises(YunohostError):
        user_group_update("alice", remove=["alice"])
    assert "alice" in user_group_list()["groups"]["alice"]["members"]

def test_update_group_add_user_that_doesnt_exist():
    # Check add bad user in group
    with pytest.raises(YunohostError):
        user_group_update("dev", add=["doesnt_exist"])

    assert "doesnt_exist" not in user_group_list()["groups"]["dev"]["members"]
