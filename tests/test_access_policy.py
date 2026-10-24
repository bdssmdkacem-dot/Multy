import unittest

from backend.access_policy import Company, Principal, can_access_company, is_authorized


FIRM_A = "firm-a"
FIRM_B = "firm-b"
ATLAS = Company("atlas", FIRM_A)
ARGAN = Company("argan", FIRM_A)
OTHER_FIRM = Company("other-client", FIRM_B)


class AccessPolicyTests(unittest.TestCase):
    def setUp(self):
        self.admin = Principal("u-admin", FIRM_A, "firm_admin", frozenset())
        self.accountant = Principal("u-accountant", FIRM_A, "accountant", frozenset({"atlas"}))
        self.read_only = Principal("u-reader", FIRM_A, "read_only", frozenset({"atlas"}))

    def test_firm_admin_can_access_companies_in_own_firm(self):
        self.assertTrue(can_access_company(self.admin, ATLAS))
        self.assertTrue(can_access_company(self.admin, ARGAN))

    def test_accountant_is_limited_to_assigned_company(self):
        self.assertTrue(can_access_company(self.accountant, ATLAS))
        self.assertFalse(can_access_company(self.accountant, ARGAN))

    def test_read_only_is_limited_to_assigned_company(self):
        self.assertTrue(can_access_company(self.read_only, ATLAS))
        self.assertFalse(can_access_company(self.read_only, ARGAN))

    def test_cross_firm_access_is_denied_even_for_admin(self):
        for principal in (self.admin, self.accountant, self.read_only):
            with self.subTest(role=principal.role):
                self.assertFalse(can_access_company(principal, OTHER_FIRM))
                self.assertFalse(is_authorized(principal, OTHER_FIRM, "view"))

    def test_read_only_cannot_mutate_or_manage_members(self):
        for action in ("create", "update", "delete", "validate_document",
                       "request_document", "manage_members", "change_roles"):
            with self.subTest(action=action):
                self.assertFalse(is_authorized(self.read_only, ATLAS, action))

    def test_accountant_can_review_but_cannot_manage_members(self):
        self.assertTrue(is_authorized(self.accountant, ATLAS, "validate_document"))
        self.assertTrue(is_authorized(self.accountant, ATLAS, "request_document"))
        self.assertFalse(is_authorized(self.accountant, ATLAS, "manage_members"))
        self.assertFalse(is_authorized(self.accountant, ATLAS, "change_roles"))

    def test_unknown_role_and_unknown_action_fail_closed(self):
        unknown = Principal("u-unknown", FIRM_A, "superuser", frozenset({"atlas"}))
        self.assertFalse(can_access_company(unknown, ATLAS))
        self.assertFalse(is_authorized(self.admin, ATLAS, "execute_arbitrary_action"))

    def test_empty_firm_id_fails_closed(self):
        malformed = Principal("u-bad", "", "firm_admin", frozenset())
        self.assertFalse(can_access_company(malformed, ATLAS))


if __name__ == "__main__":
    unittest.main()
