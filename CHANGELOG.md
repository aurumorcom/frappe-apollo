## Fixes

* **Suppress Password Exceptions in API Calls**
  * Updated `get_password` calls to utilize `raise_exception=False` during OAuth token refresh and header construction. This prevents unhandled exceptions from bubbling up when credentials are temporarily unavailable.
  * Commits: [76f17dc](https://github.com/aurumorinc/frappe-apollo/commit/76f17dca), [2504651](https://github.com/aurumorinc/frappe-apollo/commit/25046515)
