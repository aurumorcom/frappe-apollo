app_name = "frappe_apollo"
app_title = "Frappe Apollo"
app_publisher = "Aurumor"
app_description = "-"
app_email = "hello@aurumor.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["frappe_controller", "frappe_cadence", "crm"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "frappe_apollo",
# 		"logo": "/assets/frappe_apollo/logo.png",
# 		"title": "Frappe Apollo",
# 		"route": "/frappe_apollo",
# 		"has_permission": "frappe_apollo.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/frappe_apollo/css/frappe_apollo.css"
# app_include_js = "/assets/frappe_apollo/js/frappe_apollo.js"

# include js, css files in header of web template
# web_include_css = "/assets/frappe_apollo/css/frappe_apollo.css"
# web_include_js = "/assets/frappe_apollo/js/frappe_apollo.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "frappe_apollo/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "frappe_apollo/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "frappe_apollo.utils.jinja_methods",
# 	"filters": "frappe_apollo.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "frappe_apollo.install.before_install"
after_install = "frappe_apollo.install.after_install"

# Uninstallation
# ------------

before_uninstall = "frappe_apollo.uninstall.before_uninstall"
# after_uninstall = "frappe_apollo.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "frappe_apollo.utils.before_app_install"
# after_app_install = "frappe_apollo.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "frappe_apollo.utils.before_app_uninstall"
# after_app_uninstall = "frappe_apollo.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "frappe_apollo.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Cadence": {
		"on_update": "frappe_apollo.apollo.doctype.cadence.cadence.on_update",
		"on_trash": "frappe_apollo.apollo.doctype.cadence.cadence.on_trash",
	},
	"Cadence Provider": {
		"on_update": "frappe_apollo.apollo.doctype.cadence_provider.cadence_provider.on_update"
	},
	"Communication": {"on_update": "frappe_apollo.apollo.doctype.communication.communication.on_update"},
	"Email Account": {
		"on_update": "frappe_apollo.apollo.doctype.email_account.email_account.on_update"
	},
	"Multi Channel Cadence": {
		"before_save": "frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.before_save",
		"on_update": "frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.on_update",
	},
}

scheduler_events = {
	"daily": ["frappe_apollo.apollo.doctype.email_account.email_account.enqueue_get_email_accounts"]
}

controller_events = {
	"frappe_apollo.apollo.doctype.email_account.email_account.get_email_accounts": {
		"rate_limit_per_minute": 50,
		"rate_limit_per_hour": 200,
		"rate_limit_per_day": 600,
		"retries": 3,
		"timeout": 300,
	},
	"frappe_apollo.apollo.doctype.apollo_field.apollo_field.create_a_field": {
		"rate_limit_per_minute": 50,
		"rate_limit_per_hour": 200,
		"rate_limit_per_day": 600,
		"retries": 3,
		"timeout": 300,
	},
	"frappe_apollo.apollo.doctype.apollo_field.apollo_field.provision_a_field": {
		"rate_limit_per_minute": 50,
		"retries": 3,
		"timeout": 300,
	},
	"frappe_apollo.apollo.doctype.apollo_field.apollo_field.enqueue_provision_cadence_fields": {
		"rate_limit_per_minute": 50,
		"retries": 3,
		"timeout": 300,
	},
	"frappe_apollo.webhook.process_webhook": {"rate_limit_per_minute": 50, "retries": 3, "timeout": 300},
	"frappe_apollo.apollo.doctype.cadence.cadence.update_sequence_steps": {
		"rate_limit_per_minute": 50,
		"retries": 3,
		"timeout": 300,
	},
	"frappe_apollo.apollo.doctype.cadence.cadence.provision_sequences_fields_and_steps": {
		"rate_limit_per_minute": 50,
		"retries": 3,
		"timeout": 300,
	},
	"frappe_apollo.apollo.doctype.cadence.cadence.update_sequences": {
		"rate_limit_per_minute": 50,
		"retries": 3,
		"timeout": 300,
	},
	"frappe_apollo.apollo.doctype.cadence.cadence.archive_sequences": {
		"rate_limit_per_minute": 50,
		"retries": 3,
		"timeout": 300,
	},
	"frappe_apollo.apollo.doctype.cadence.cadence.toggle_cadence_mccs": {
		"rate_limit_per_minute": 50,
		"retries": 3,
		"timeout": 300,
	},
	"frappe_apollo.apollo.doctype.cadence.cadence._disable_cadence_mccs": {
		"rate_limit_per_minute": 50,
		"retries": 3,
		"timeout": 300,
	},
	"frappe_apollo.apollo.doctype.apollo_account.apollo_account.provision_sequence": {
		"rate_limit_per_minute": 50,
		"retries": 3,
		"timeout": 300,
	},
	"frappe_apollo.apollo.doctype.crm_lead.crm_lead._create_a_contact": {
		"rate_limit_per_minute": 50,
		"retries": 3,
		"timeout": 300,
	},
	"frappe_apollo.apollo.doctype.crm_lead.crm_lead.create_a_contact": {
		"rate_limit_per_minute": 50,
		"retries": 3,
		"timeout": 300,
	},
	"frappe_apollo.apollo.doctype.crm_lead.crm_lead.update_a_contact": {
		"rate_limit_per_minute": 50,
		"retries": 3,
		"timeout": 300,
	},
	"frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.add_contact_to_sequence": {
		"rate_limit_per_minute": 50,
		"retries": 3,
		"timeout": 300,
	},
	"frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence._assign_contact_to_sequence": {
		"rate_limit_per_minute": 50,
		"retries": 3,
		"timeout": 300,
	},
	"frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence.update_sequence_contact_status": {
		"rate_limit_per_minute": 50,
		"retries": 3,
		"timeout": 300,
	},
	"frappe_apollo.apollo.doctype.multi_channel_cadence.multi_channel_cadence._stop_contact_in_sequence": {
		"rate_limit_per_minute": 50,
		"retries": 3,
		"timeout": 300,
	},
	"frappe_apollo.apollo.doctype.communication.communication.update_a_contact": {
		"rate_limit_per_minute": 50,
		"retries": 3,
		"timeout": 300,
	},
}

# after_install = "frappe_apollo.setup.after_install"

fixtures = [
	{"dt": "Custom Field", "filters": [["module", "=", "Apollo"]]},
	{"dt": "Property Setter", "filters": [["module", "in", ["Apollo", "frappe_apollo"]]]},
]


# Testing
# -------

# before_tests = "frappe_apollo.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "frappe_apollo.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "frappe_apollo.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "frappe_apollo.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["frappe_apollo.utils.before_request"]
# after_request = ["frappe_apollo.utils.after_request"]

# Job Events
# ----------
# before_job = ["frappe_apollo.utils.before_job"]
# after_job = ["frappe_apollo.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"frappe_apollo.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
