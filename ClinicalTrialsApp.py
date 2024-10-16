import json
import os
import openai
from openai import OpenAI
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Initialize the Flask app
app = Flask(__name__)

os.environ['OPEN_API_KEY'] = "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"
client = OpenAI( api_key=os.environ.get('OPEN_API_KEY') )

# Directory to save uploaded files
UPLOAD_FOLDER = '/Users/vijaykirandegala/Downloads/FHIR_STU4_Filtering/Reference_code/App/mcode-transilator/Uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Predefined file path for existing files in the dropdown
EXISTING_FILES_PATH = '/Users/vijaykirandegala/Downloads/FHIR_STU4_Filtering/Sample_FHIR_Data/STU1/female/'

# Function to extract patient data
def extract_patient_data(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    data = data['entry']
    
    # Variables to hold extracted data
    patient_data = {}
    conditions = []
    care_plans = []
    encounters = []
    diagnostic_reports = []
    observations = []
    procedures = []

    for entry in data:
        resource = entry['resource']
        resource_type = resource['resourceType']
        
        if resource_type == "Patient":
            patient = resource
            patient_data['name'] = patient['name'][0]['family'] if 'name' in patient else None
            patient_data['gender'] = patient.get('gender', None)
            patient_data['birthDate'] = patient.get('birthDate', None)
            
            for ext in patient.get('extension', []):
                if ext['url'] == 'http://hl7.org/fhir/us/core/StructureDefinition/us-core-race':
                    patient_data['race'] = ext['extension'][0]['valueCoding']['display']
                elif ext['url'] == 'http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity':
                    patient_data['ethnicity'] = ext['extension'][0]['valueCoding']['display']
            patient_data['address'] = patient['address'][0]['city'] if 'address' in patient else None
        
        elif resource_type == "Condition":
            condition = resource
            conditions.append({
                'condition': condition['code']['coding'][0]['display'],
                'clinicalStatus': condition.get('clinicalStatus', {}).get('coding', [{}])[0].get('code', None),
                'verificationStatus': condition.get('verificationStatus', {}).get('coding', [{}])[0].get('code', None),
                'onsetDateTime': condition.get('onsetDateTime', None)
            })
        
        elif resource_type == "CarePlan":
            care_plan = resource
            care_plans.append({
                'plan': care_plan['activity'][0]['detail']['code']['coding'][0]['display'] if 'activity' in care_plan else None,
                'status': care_plan.get('status', None),
                'start': care_plan.get('period', {}).get('start', None)
            })
        
        elif resource_type == "Encounter":
            encounter = resource
            encounters.append({
                'type': encounter['type'][0]['coding'][0]['display'] if 'type' in encounter else None,
                'date': encounter.get('period', {}).get('start', None)
            })
        
        elif resource_type == "DiagnosticReport":
            diagnostic_report = resource
            diagnostic_reports.append({
                'report': diagnostic_report['code']['coding'][0]['display'] if 'code' in diagnostic_report else None,
                'effectiveDateTime': diagnostic_report.get('effectiveDateTime', None)
            })
        
        elif resource_type == "Observation":
            observation = resource
            observations.append({
                'observation': observation['code']['coding'][0]['display'] if 'code' in observation else None,
                'value': observation.get('valueQuantity', {}).get('value', None),
                'unit': observation.get('valueQuantity', {}).get('unit', None),
                'effectiveDateTime': observation.get('effectiveDateTime', None)
            })
        
        elif resource_type == "Procedure":
            procedure = resource
            procedures.append({
                'procedure': procedure['code']['coding'][0]['display'] if 'code' in procedure else None,
                'status': procedure.get('status', None),
                'performedDateTime': procedure.get('performedDateTime', None)
            })
    
    return {
        'patient_data': patient_data,
        'conditions': conditions,
        'care_plans': care_plans,
        'encounters': encounters,
        'diagnostic_reports': diagnostic_reports,
        'observations': observations,
        'procedures': procedures
    }

# Function to interact with OpenAI API
def generate_clinical_trial_response(prompt):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that finds clinical trials matching a patient's profile. Provide your responses in well-formatted HTML suitable for display on a web page."},
            {"role": "user", "content": prompt}
        ],
    )
    return response.choices[0].message.content

# Function to interact with OpenAI API
def generate_patient_data_response(prompt):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant tasked with reading patient data and outputting only the translated patient data, without including any additional information or explanations. Please structure the output in a clean and organized format."},
            {"role": "user", "content": prompt}
        ],
    )
    return response.choices[0].message.content

# Route to upload the patient file or use a predefined file from the dropdown
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Check if a file was uploaded
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            print(file_path)
            # Extract data from uploaded file
            extracted_data = extract_patient_data(file_path)

        # Check if an existing file was selected from the dropdown
        elif 'existingFile' in request.form:
            selected_file = request.form['existingFile']
            file_path = os.path.join(EXISTING_FILES_PATH, selected_file) + '.json'
            
            # Extract data from the selected file
            extracted_data = extract_patient_data(file_path)

        else:
            return jsonify({'error': 'No file uploaded or selected.'}), 400

        # Generate prompt based on extracted data
        prompt = f"Patient data: {extracted_data}. Find the Clinical Trials That Match this profile."
        Clinical_trials_matched = generate_clinical_trial_response(prompt)

        prompt = f"""Patient data: {extracted_data}. Write a detailed, structured description of the patient’s clinical data to match them to relevant clinical trials. Ensure that the paragraph includes the following key details:

Patient demographics: Include age, gender, race/ethnicity, location, and other relevant identifiers.
Diagnosis: State the primary diagnosis, including any relevant staging or grading, and secondary diagnoses, if applicable.
Medical history: Summarize pertinent medical history, including prior treatments, surgeries, or conditions.
Genetic information: Highlight any genetic mutations or biomarkers relevant to the patient’s condition.
Symptoms and presentation: Describe the current symptoms, onset, and progression of the disease.
Treatment history: Include current and past treatments, such as medications, therapies, or clinical interventions, and the patient’s response to these treatments.
Relevant lab results: Provide key lab findings, imaging results, or other diagnostic data that are crucial for trial eligibility.
Additional considerations: Note any lifestyle factors, family history of the disease, or other conditions that might affect trial participation.

The final paragraph should be well-organized, coherent, and written in a narrative style to help an LLM efficiently retrieve relevant clinical trials through a RAG system.

"""
        readble_patient_data = generate_patient_data_response(prompt)

        return jsonify({
            'extracted_data': extracted_data,
            'Clinical_trials_matched': Clinical_trials_matched,
            'readble_patient_data' : readble_patient_data
        })

    files = os.listdir(EXISTING_FILES_PATH)
    files = [x.replace('.json','') for x in files]

    return render_template('Home.html', files=files)

if __name__ == "__main__":
    app.run(debug=True)