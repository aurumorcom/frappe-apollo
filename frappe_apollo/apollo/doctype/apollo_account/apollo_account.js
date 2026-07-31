frappe.ui.form.on('Apollo Account', {
	onload: function(frm) {
		['api_key', 'client_secret', 'refresh_token', 'access_token', 'webhook_bearer_token'].forEach(fieldname => {
			if (frm.fields_dict[fieldname]) {
				frm.fields_dict[fieldname].disable_password_checks();
			}
		});
	},
	refresh: function(frm) {
		if (!frm.is_new() && frm.doc.client_id) {
			if (frm.doc.status === "Unauthorized") {
				frm.add_custom_button(__('Authorize'), function() {
					frm.call({
						method: 'get_authorization_url',
						doc: frm.doc,
						callback: function(r) {
							if (r.message) {
								window.location.href = r.message;
							}
						}
					});
				});
			} else if (frm.doc.status === "Authorized") {
				frm.add_custom_button(__('Unauthorize'), function() {
					frm.call({
						method: 'clear_tokens',
						doc: frm.doc,
						callback: function(r) {
							frm.reload_doc();
						}
					});
				});
			}
		}
	}
});
