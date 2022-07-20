from marshmallow import Schema, fields


class ActivationAuthClinician(Schema):
    uuid = fields.String(required=True, description="Clinician UUID")
    send_entry_identifier = fields.String(required=False, allow_none=True)
    login_active = fields.Boolean(required=True)
    products = fields.List(fields.Dict(), required=True)
    groups = fields.List(fields.String(), required=True)
    contract_expiry_eod_date = fields.String(required=True, allow_none=True)
