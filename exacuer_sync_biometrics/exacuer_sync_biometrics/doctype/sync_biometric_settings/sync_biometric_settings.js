// Copyright (c) 2025, sushant and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Sync Biometric Settings", {
// 	refresh(frm) {

// 	},
// });

// frappe.ui.form.on('Sync Biometric Settings', {
//     url: function(frm) {
//         if (frm.doc.url) {
//             try {
//                 const urlObj = new URL(frm.doc.url);
//                 const keyValue = urlObj.searchParams.get("APIKey");

//                 if (keyValue) {
//                     frm.set_value("key", keyValue);
//                 } else {
//                     frappe.msgprint(__('No "key" parameter found in the URL.'));
//                 }
//             } catch (error) {
//                 frappe.msgprint(__('Invalid URL format.'));
//             }
//         }
//     },
    
// });

frappe.ui.form.on('Sync Biometric Settings', {
    url: function(frm) {
        if (frm.doc.url) {
            try {
                const urlObj = new URL(frm.doc.url);
                const keyValue = urlObj.searchParams.get("APIKey");

                if (keyValue) {
                    frm.set_value("key", keyValue);
                } else {
                    frappe.msgprint(__('No "key" parameter found in the URL.'));
                }
            } catch (error) {
                frappe.msgprint(__('Invalid URL format.'));
            }
        }
    },
    refresh(frm) {
        frm.add_custom_button("Load Mapping Field Options", () => {
            frm.trigger("load_mapping_field_options");
        });
    },

    load_mapping_field_options(frm) {
        if (!frm.doc.name || !frm.doc.map_fields || frm.doc.map_fields.length === 0) {
            frappe.msgprint("Please add rows to the Map Fields table first.");
            return;
        }

        // Fetch both field lists in parallel
        Promise.all([
            frappe.call({
                method: "exacuer_sync_biometrics.exacuer_sync_biometrics.doctype.sync_biometric_settings.sync_biometric_settings.get_api_fields_from_response",
                args: { docname: frm.doc.name }
            }),
            frappe.call({
                method: "exacuer_sync_biometrics.exacuer_sync_biometrics.doctype.sync_biometric_settings.sync_biometric_settings.get_employee_checkin_fields"
            })
        ]).then(([api_res, map_res]) => {
            const api_fields = api_res.message || [];
            const checkin_fields = map_res.message || [];

            // ✅ Apply default options so collapsed rows get them too
            frm.fields_dict.map_fields.grid.update_docfield_property("api_field", "options", api_fields.join("\n"));
            frm.fields_dict.map_fields.grid.update_docfield_property("map_field", "options", checkin_fields.join("\n"));

            // ✅ For expanded rows: also update live fields inside the form
            frm.fields_dict.map_fields.grid.grid_rows.forEach(row => {
                if (row.grid_form) {
                    const api_field = row.grid_form.fields_dict.api_field;
                    const map_field = row.grid_form.fields_dict.map_field;

                    if (api_field && map_field) {
                        api_field.df.options = api_fields.join('\n');
                        map_field.df.options = checkin_fields.join('\n');

                        api_field.refresh();
                        map_field.refresh();
                    }
                }
            });

            frm.refresh_field("map_fields");
            frappe.msgprint("Dropdown options loaded for all rows.");
        });
    }
});
