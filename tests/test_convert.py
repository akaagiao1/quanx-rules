import unittest

from quanx_rules.convert import ConversionError, convert_document


def document(*rules):
    return {"version": 2, "rules": list(rules)}


class ConversionTests(unittest.TestCase):
    def test_match_types_and_subdomain_boundary(self):
        result = convert_document(document({
            "domain": ["EXAMPLE.com", "例子.中国"],
            "domain_suffix": ["example.net", ".sub.example.net"],
            "domain_keyword": "ads-",
        }))
        self.assertEqual(result.lines, [
            "host,example.com,proxy",
            "host,xn--fsqu00a.xn--fiqs8s,proxy",
            "host-keyword,ads-,proxy",
            "host-suffix,example.net,proxy",
            "host-wildcard,*.sub.example.net,proxy",
        ])
        self.assertEqual(result.source_entries, 5)

    def test_cidr_versions_normalize_and_deduplicate(self):
        result = convert_document(document({"ip_cidr": [
            "192.0.2.9/24", "192.0.2.0/24", "2001:0db8::1/32", "203.0.113.1",
        ]}))
        self.assertEqual(result.lines, [
            "ip-cidr,192.0.2.0/24,proxy",
            "ip-cidr,203.0.113.1/32,proxy",
            "ip6-cidr,2001:db8::/32,proxy",
        ])
        self.assertEqual(result.source_entries, 4)

    def test_regex_is_retained_without_broadening(self):
        result = convert_document(document({"domain": "ok.test", "domain_regex": ["^ad[0-9]+\\.test$"]}))
        self.assertEqual(result.lines, ["host,ok.test,proxy"])
        self.assertEqual(result.unsupported[0]["value"], "^ad[0-9]+\\.test$")
        self.assertEqual(result.unsupported[0]["field"], "domain_regex")
        self.assertEqual(result.source_entries, 2)

    def test_regex_only_and_empty_have_no_fake_rules(self):
        self.assertEqual(convert_document(document({"domain_regex": "a+"})).lines, [])
        self.assertEqual(convert_document(document()).source_entries, 0)
        self.assertEqual(convert_document(document({"domain": []})).lines, [])

    def test_unsafe_values_are_rejected(self):
        for key, value in [
            ("domain", "ok.test,reject"), ("domain_keyword", "ads\nfinal,direct"),
            ("domain", "*.test"), ("domain", "has space.test"),
            ("domain_suffix", "."), ("domain", ""),
            ("ip_cidr", "999.0.0.1/32"), ("domain_keyword", " a"),
        ]:
            with self.subTest(key=key, value=value), self.assertRaises(ConversionError):
                convert_document(document({key: value}))

    def test_unknown_constraints_and_invalid_shapes_fail_closed(self):
        for value in [
            {"version": 3, "rules": []}, {"version": True, "rules": []},
            {"version": 2, "rules": {}}, {"version": 2, "rules": [None]},
            {"version": 2, "rules": [], "extra": 1},
            document({"domain": "ok.test", "port": 443}),
            document({"type": "logical", "mode": "and", "rules": []}),
            document({"domain": "ok.test", "invert": True}),
            document({"domain": 12}), document({"domain": ["ok.test", None]}),
        ]:
            with self.subTest(value=value), self.assertRaises(ConversionError):
                convert_document(value)


if __name__ == "__main__":
    unittest.main()
