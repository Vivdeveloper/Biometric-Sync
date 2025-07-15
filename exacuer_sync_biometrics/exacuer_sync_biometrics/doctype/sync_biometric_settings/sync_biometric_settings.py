# Copyright (c) 2025, sushant and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document



class SyncBiometricSettings(Document):
	pass



import frappe
import json
import requests
from datetime import date
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, ParseResult

def before_save_sync_biometric_settings(doc, method):
    try:
        # Parse the URL
        parsed_url = urlparse(doc.url)
        query_params = parse_qs(parsed_url.query)

        # Extract APIKey
        api_key = query_params.get("APIKey", [None])[0]
        if api_key:
            doc.api_key = api_key
        else:
            frappe.msgprint("APIKey not found in the URL.")

        # Inject today's date into FromDate and ToDate
        today = date.today().strftime("%Y-%m-%d")
        query_params["FromDate"] = [today]
        query_params["ToDate"] = [today]

        # Rebuild the query string
        updated_query = urlencode(query_params, doseq=True)

        # Reconstruct the full URL
        updated_url = ParseResult(
            scheme=parsed_url.scheme,
            netloc=parsed_url.netloc,
            path=parsed_url.path,
            params=parsed_url.params,
            query=updated_query,
            fragment=parsed_url.fragment,
        )
        final_url = urlunparse(updated_url)

        # Update doc.url (optional, for recordkeeping)
        # doc.url = final_url

        # Make the request
        response = requests.get(final_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Save first 2 entries from response
        if isinstance(data, list):
            doc.response = frappe.as_json(data[:2])
        elif isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list):
                    doc.response = frappe.as_json(value[:2])
                    break
            else:
                doc.response = "[]"
        else:
            doc.response = "[]"

    except Exception as e:
        frappe.throw(f"Error during biometric sync: {str(e)}")



@frappe.whitelist()
def get_employee_checkin_fields():
    print("################################################################")
    meta = frappe.get_meta("Employee Checkin")
    fields = [df.fieldname for df in meta.fields if df.fieldname]
    print(fields)
    return fields

@frappe.whitelist()
def get_api_fields_from_response(docname):
    doc = frappe.get_doc("Sync Biometric Settings", docname)
    try:
        data = json.loads(doc.response)
        print(data)
        if isinstance(data, list) and data:
            print("#####",list(data[0].keys()))
            return list(data[0].keys())
        elif isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    return list(v[0].keys())
        return []
    except Exception as e:
        return []


import frappe
import requests
import json
from datetime import datetime
from frappe.utils import nowdate

@frappe.whitelist()
def sync_biometric_checkins():
    frappe.logger("biometric_sync").info("Running sync_biometric_checkins()")
    print(">>>> Starting sync_biometric_checkins()")
    frappe.log_error(f"Failed to fetch data from ", "Biometric Sync")
    today = nowdate()
    print("Today",today)
    settings_list = frappe.get_all("Sync Biometric Settings", filters={"enabled": 1}, fields=["name", "url"])

    

    for settings in settings_list:
        try:
            doc = frappe.get_doc("Sync Biometric Settings", settings.name)
            print("Today",today)
            # Replace {FromDate} and {ToDate} in URL with today's date
            url = doc.url.replace("{FromDate}", today).replace("{ToDate}", today)
            print("Today",today)
            print("",url)
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                frappe.log_error(f"Failed to fetch data from {url}", "Biometric Sync")
                continue

            data = response.json()
            print(data)

            # If nested list inside dict, extract it
            if isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, list):
                        data = v
                        break

            if not isinstance(data, list):
                frappe.log_error(f"Unexpected JSON format from {url}", "Biometric Sync")
                continue

            # Build field mapping from child table
            field_map = {row.map_field: row.api_field for row in doc.map_fields if row.api_field and row.map_field}

            for entry in data:
                checkin_data = {}
                for target_field, source_field in field_map.items():
                    checkin_data[target_field] = entry.get(source_field)
                
                print("Fetched Entry:", checkin_data)
                frappe.logger("biometric_sync").info(f"Fetched entry: {checkin_data}")

                # Required fields
                device_id = checkin_data.get("device_id")
                checkin_time = checkin_data.get("time")

                if not device_id or not checkin_time:
                    print("Skipping: Missing device_id or time")
                    continue

                employee_info = frappe.db.get_value("Employee", {"attendance_device_id": device_id}, ["name", "employee_name"], as_dict=True)

                if not employee_info:
                    print(f"Skipping: No employee found with attendance_device_id = {device_id}")
                    continue
                
                checkin_data["employee"] = employee_info.name
                checkin_data["employee_name"] = employee_info.employee_name
                
                # Avoid duplicate
                if frappe.db.exists("Employee Checkin", {
                    "employee": checkin_data["employee"],
                    "time": checkin_time
                }):
                    print(f"Skipping duplicate check-in for {checkin_data['employee']} at {checkin_time}")
                    continue
                
                # Create Employee Checkin
                checkin = frappe.new_doc("Employee Checkin")
                checkin.update(checkin_data)
                checkin.insert(ignore_permissions=True)
                print(f"✅ Inserted: {checkin.employee} ({checkin.employee_name}) at {checkin.time}")
                frappe.logger("biometric_sync").info(f"Inserted check-in for {checkin.employee} ({checkin.employee_name}) at {checkin.time}")

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Biometric Sync Error")
