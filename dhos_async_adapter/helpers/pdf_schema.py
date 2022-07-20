from marshmallow import INCLUDE, Schema, fields


class PatientSchema(Schema):
    class Meta:
        unknown = INCLUDE

    uuid = fields.String(required=True)
    first_name = fields.String(required=True)
    last_name = fields.String(required=True)
    nhs_number = fields.String(allow_none=True)


class GdmPatientSchema(Schema):
    class Meta:
        unknown = INCLUDE

    medications = fields.Dict(keys=fields.String(), required=True)
    patient = fields.Nested(PatientSchema, required=True)
    pregnancy = fields.Dict(keys=fields.String(), required=True)
    readings_plan = fields.Dict(keys=fields.String(), required=True)
    management_plan = fields.Dict(keys=fields.String(), required=True)
    diabetes = fields.Dict(keys=fields.String(), required=True)
    deliveries = fields.List(fields.Dict(), required=True)
    blood_glucose_readings = fields.List(fields.Dict(), required=True)
    latest_visit = fields.Dict(keys=fields.String(), required=True)
    medication_plan = fields.Dict(keys=fields.String(), required=True)


class ClinicianSchema(Schema):
    class Meta:
        unknown = INCLUDE
        ordered = True

    uuid = fields.String(required=True)
    first_name = fields.String(required=True)
    last_name = fields.String(required=True)


class WardSchema(Schema):
    class Meta:
        unknown = INCLUDE

    pdf_data = fields.List(fields.Dict(), required=True)
    hospital_name = fields.String(required=True)
    ward_name = fields.String(required=True)
    report_month = fields.String(example="July", required=True)
    report_year = fields.String(example="2019", required=True)
    location_uuid = fields.String(required=True)
