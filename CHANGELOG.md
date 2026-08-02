# Changelog v16.4.0

## Breaking Changes

* **API Key Field Type Update to Password**
  * Description: Updated the API key field from Data type to Password type to properly secure sensitive credentials ([067da3b](https://github.com/aurumorinc/frappe-apollo/commit/067da3b8)). Severity: High.
  * Migration Path: Update any automated API integrations or scripts that interact with the API key field directly via the database to accommodate the new password field type.

## Improvements

* **Test Infrastructure Refactoring**
  * Description: Refactored mock object creation, updated return values, and fixed mock setups in cadence and OAuth tests ([dcf68c1](https://github.com/aurumorinc/frappe-apollo/commit/dcf68c1b), [8327838](https://github.com/aurumorinc/frappe-apollo/commit/83278388), [3137a7b](https://github.com/aurumorinc/frappe-apollo/commit/3137a7b3)).

## Bug Fixes

* **Exception Handling and OAuth Error Detection**
  * Description: Added explicit exception re-raising in error handlers and improved OAuth error detection for authentication failures (400, 401, 403) ([60a62c6](https://github.com/aurumorinc/frappe-apollo/commit/60a62c64)).

## Documentation

* **OAuth Token Refresh Documentation**
  * Description: Added token refresh flowchart diagram documenting OAuth token auto-refresh flow ([0a72ce5](https://github.com/aurumorinc/frappe-apollo/commit/0a72ce56)).
* **Risks and Technical Debt Restructuring**
  * Description: Restructured risks and technical debt documentation ([53041ff](https://github.com/aurumorinc/frappe-apollo/commit/53041ff1)).

## Other

* **Apollo Account Setup Simplification**
  * Description: Simplified the `setUp` method to fetch or create Apollo Account documents in a single expression ([1abba65](https://github.com/aurumorinc/frappe-apollo/commit/1abba65e)).
