import flask
import logging
import psycopg2
import hashlib
import jwt
import datetime
from flask import jsonify, request, g
from functools import wraps

app = flask.Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'  
logging.basicConfig(level=logging.INFO)

StatusCodes = {
    'success': 200,
    'api_error': 400,
    'internal_error': 500,
}

def db_connection():
    db = psycopg2.connect(
        user='aulaspl',
        password='aulaspl',
        host='127.0.0.1',
        port='5432',
        database='Projeto'
    )
    return db

def generate_password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token(username):
    payload = {
        'username': username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)  
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    return token

def verify_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            token = request.json.get('token')
        if not token:
            return jsonify({"status": StatusCodes['api_error'], "errors": "Token is missing!"}), StatusCodes['api_error']
        try:
            if token.startswith('Bearer '):
                token = token.split(' ')[1]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            g.user = data['username']
        except Exception as e:
            return jsonify({"status": StatusCodes['api_error'], "errors": str(e)}), StatusCodes['api_error']
        return f(*args, **kwargs)
    return decorated

def get_user_role(username):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT person_id FROM person WHERE username = %s", (username,))
    person_id = cursor.fetchone()[0]
    cursor.execute("SELECT * FROM pacient WHERE person_person_id = %s", (person_id,))
    patient = cursor.fetchone()
    cursor.close()
    conn.close()
    return 'patient' if patient else 'other'

def check_availability(entity_id, start_time, end_time):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * 
        FROM agenda 
        WHERE employer_id = %s AND data_inicio < %s AND data_fim > %s
    """, (entity_id, end_time, start_time))
    conflicts = cursor.fetchall()
    cursor.close()
    conn.close()
    return len(conflicts) == 0

def get_available_nurses(start_time, end_time):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT n.employer_person_person_id 
        FROM nurse n
        WHERE n.employer_person_person_id NOT IN (
            SELECT employer_id 
            FROM agenda a
            WHERE a.data_inicio < %s AND a.data_fim > %s
        )
        LIMIT 5
    """, (end_time, start_time))
    available_nurses = cursor.fetchall()
    cursor.close()
    conn.close()
    return [nurse[0] for nurse in available_nurses]

def acquire_lock(lock_id):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT pg_advisory_lock(%s);", (lock_id,))
    conn.commit()
    cursor.close()
    conn.close()

def release_lock(lock_id):
    conn = db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT pg_advisory_unlock(%s);", (lock_id,))
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/dbproj/register/<user_type>', methods=['POST'])
def register_user(user_type):
    data = request.json
    name = data.get('name')
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    contract_details = data.get('contract_details')
    hierarchy = data.get('hierarchy') if user_type == 'nurse' else None
    specialization = data.get('specialization') if user_type == 'doctor' else None
    hashed_password = generate_password_hash(password)
    
    lock_id = 1

    try:
        acquire_lock(lock_id)
        
        conn = db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT person_id FROM person WHERE email = %s OR username = %s", (email, username))
        existing_user = cursor.fetchone()
        if existing_user:
            return jsonify({"status": StatusCodes['api_error'], "errors": "User with this email or username already exists", "results": None}), StatusCodes['api_error']
        
        cursor.execute(
            "INSERT INTO person (name, email, username, password) VALUES (%s, %s, %s, %s) RETURNING person_id",
            (name, email, username, hashed_password)
        )
        person_id = cursor.fetchone()[0]
        
        if user_type == 'patient':
            cursor.execute(
                "INSERT INTO pacient (person_person_id) VALUES (%s)",
                (person_id,)
            )
        else:
            cursor.execute(
                "INSERT INTO employer (contract_details, person_person_id) VALUES (%s, %s) RETURNING person_person_id",
                (contract_details, person_id)
            )
            employer_id = cursor.fetchone()[0]
            
            if user_type == 'assistant':
                cursor.execute(
                    "INSERT INTO assistant (employer_person_person_id) VALUES (%s)",
                    (employer_id,)
                )
            elif user_type == 'nurse':
                cursor.execute(
                    "INSERT INTO nurse (hierarchy, employer_person_person_id) VALUES (%s, %s)",
                    (hierarchy, employer_id)
                )
            elif user_type == 'doctor':
                cursor.execute(
                    "INSERT INTO doctors (specialization, employer_person_person_id) VALUES (%s, %s)",
                    (specialization, employer_id)
                )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"status": StatusCodes['success'], "errors": None, "results": person_id}), StatusCodes['success']
    
    except Exception as e:
        logging.error(f"Error registering user: {str(e)}")
        return jsonify({"status": StatusCodes['internal_error'], "errors": str(e), "results": None}), StatusCodes['internal_error']
    finally:
        release_lock(lock_id)

@app.route('/dbproj/user', methods=['PUT'])
def authenticate_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    hashed_password = generate_password_hash(password)
    
    try:
        conn = db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM person WHERE username = %s AND password = %s",
            (username, hashed_password)
        )
        user = cursor.fetchone()
        
        if user:
            token = generate_token(username)
            return jsonify({"status": StatusCodes['success'], "errors": None, "results": token}), StatusCodes['success']
        else:
            return jsonify({"status": StatusCodes['api_error'], "errors": "Invalid credentials", "results": None}), StatusCodes['api_error']
    
    except Exception as e:
        logging.error(f"Error authenticating user: {str(e)}")
        return jsonify({"status": StatusCodes['internal_error'], "errors": str(e), "results": None}), StatusCodes['internal_error']
    finally:
        cursor.close()
        conn.close()

@app.route('/dbproj/appointment', methods=['POST'])
@verify_token
def schedule_appointment():
    user_role = get_user_role(g.user)
    if user_role != 'patient':
        return jsonify({"status": StatusCodes['unauthorized'], "errors": "Only patients can schedule appointments", "results": None}), StatusCodes['unauthorized']
    
    data = request.json
    doctor_id = data.get('doctor_id')
    appointment_timestamp = data.get('timestamp')

    if not appointment_timestamp:
        return jsonify({"status": StatusCodes['api_error'], "errors": "Date is required", "results": None}), StatusCodes['api_error']
    
    try:
        appointment_date = datetime.datetime.strptime(appointment_timestamp, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return jsonify({"status": StatusCodes['api_error'], "errors": "Invalid date format. Expected format: YYYY-MM-DDTHH:MM:SS", "results": None}), StatusCodes['api_error']

    appointment_end = appointment_date + datetime.timedelta(minutes=30)
    
    lock_id = 2

    try:
        acquire_lock(lock_id)
        
        conn = db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT d.employer_person_person_id 
            FROM doctors d
            JOIN employer e ON d.employer_person_person_id = e.person_person_id
            WHERE e.person_person_id = %s
        """, (doctor_id,))
        doctor_result = cursor.fetchone()
        if not doctor_result:
            return jsonify({"status": StatusCodes['api_error'], "errors": "Doctor not found", "results": None}), StatusCodes['api_error']

        cursor.execute("SELECT person_id FROM person WHERE username = %s", (g.user,))
        person_result = cursor.fetchone()
        if not person_result:
            return jsonify({"status": StatusCodes['api_error'], "errors": "User not found", "results": None}), StatusCodes['api_error']
        
        person_id = person_result[0]

        if not check_availability(person_id, appointment_date, appointment_end):
            return jsonify({"status": StatusCodes['api_error'], "errors": "Patient has a conflict", "results": None}), StatusCodes['api_error']
        if not check_availability(doctor_id, appointment_date, appointment_end):
            return jsonify({"status": StatusCodes['api_error'], "errors": "Doctor has a conflict", "results": None}), StatusCodes['api_error']

        available_nurses = get_available_nurses(appointment_date, appointment_end)
        if len(available_nurses) < 2:
            return jsonify({"status": StatusCodes['api_error'], "errors": "Not enough nurses available", "results": None}), StatusCodes['api_error']

        for nurse_id in available_nurses:
            if not check_availability(nurse_id, appointment_date, appointment_end):
                return jsonify({"status": StatusCodes['api_error'], "errors": "Nurse has a conflict", "results": None}), StatusCodes['api_error']

        cursor.execute(
            "INSERT INTO agenda (data_inicio, data_fim, employer_id, type, event_id) VALUES (%s, %s, %s, %s, NULL) RETURNING id_agenda",
            (appointment_date, appointment_end, doctor_id, 'appointment')
        )
        agenda_id_doctor = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO agenda (data_inicio, data_fim, employer_id, type, event_id) VALUES (%s, %s, %s, %s, NULL) RETURNING id_agenda",
            (appointment_date, appointment_end, person_id, 'patient_appointment')
        )
        agenda_id_patient = cursor.fetchone()[0]

       
        cursor.execute(
            "INSERT INTO appointment (appointment_date, pacient_id, price, agenda_id_agenda, pacient_person_person_id, doctors_employer_person_person_id) VALUES (%s, %s, %s, %s, %s, %s) RETURNING appointment_id",
            (appointment_date, person_id, 40, agenda_id_doctor, person_id, doctor_id)
        )
        appointment_id = cursor.fetchone()[0]

       
        cursor.execute(
            "UPDATE agenda SET event_id = %s WHERE id_agenda = %s",
            (appointment_id, agenda_id_doctor)
        )

        cursor.execute(
            "UPDATE agenda SET event_id = %s WHERE id_agenda = %s",
            (appointment_id, agenda_id_patient)
        )

       
        for nurse_id in available_nurses[:2]:  
            cursor.execute(
                "INSERT INTO nurse_appointment (nurse_employer_person_person_id, appointment_appointment_id) VALUES (%s, %s)",
                (nurse_id, appointment_id)
            )
            cursor.execute(
                "INSERT INTO agenda (data_inicio, data_fim, employer_id, type, event_id) VALUES (%s, %s, %s, %s, %s)",
                (appointment_date, appointment_end, nurse_id, 'nurse_appointment', appointment_id)
            )

        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"status": StatusCodes['success'], "errors": None, "results": appointment_id}), StatusCodes['success']
    
    except Exception as e:
        logging.error(f"Error scheduling appointment: {str(e)}")
        return jsonify({"status": StatusCodes['internal_error'], "errors": str(e), "results": None}), StatusCodes['internal_error']
    finally:
        release_lock(lock_id)



@app.route('/dbproj/appointments/<int:patient_user_id>', methods=['GET'])
@verify_token
def get_appointments(patient_user_id):
    try:
        conn = db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT person_id FROM person WHERE username = %s", (g.user,))
        user_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT * FROM assistant WHERE employer_person_person_id = %s", (user_id,))
        is_assistant = cursor.fetchone() is not None

        if not is_assistant and user_id != patient_user_id:
            return jsonify({"status": StatusCodes['api_error'], "errors": "Only assistants and the target patient can access this endpoint", "results": None}), StatusCodes['api_error']

        cursor.execute("""
            SELECT a.appointment_id, a.doctors_employer_person_person_id AS doctor_id, a.appointment_date
            FROM appointment a
            WHERE a.pacient_person_person_id = %s
        """, (patient_user_id,))
        
        appointments = cursor.fetchall()
        
        results = []
        for appointment in appointments:
            results.append({
                "id": appointment[0],
                "doctor_id": appointment[1],
                "date": appointment[2]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({"status": StatusCodes['success'], "errors": None, "results": results}), StatusCodes['success']
    
    except Exception as e:
        logging.error(f"Error fetching appointments: {str(e)}")
        return jsonify({"status": StatusCodes['internal_error'], "errors": str(e), "results": None}), StatusCodes['internal_error']


@app.route('/dbproj/surgery', methods=['POST'])
@verify_token
def schedule_surgery():
    data = request.json
    patient_id = data.get('patient_id')
    doctor_id = data.get('doctor')
    surgery_date = datetime.datetime.strptime(data.get('date'), "%Y-%m-%dT%H:%M:%S")
    surgery_end = surgery_date + datetime.timedelta(hours=2)
    try:
        conn = db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT person_id FROM person WHERE username = %s", (g.user,))
        user_result = cursor.fetchone()
        if not user_result:
            return jsonify({"status": StatusCodes['api_error'], "errors": "User not found", "results": None}), StatusCodes['api_error']
        
        user_id = user_result[0]
        cursor.execute("SELECT * FROM assistant WHERE employer_person_person_id = %s", (user_id,))
        if not cursor.fetchone():
            return jsonify({"status": StatusCodes['api_error'], "errors": "Only assistants can schedule surgeries", "results": None}), StatusCodes['api_error']

        cursor.execute("SELECT person_person_id FROM pacient WHERE person_person_id = %s", (patient_id,))
        if not cursor.fetchone():
            return jsonify({"status": StatusCodes['api_error'], "errors": "Patient not found", "results": None}), StatusCodes['api_error']

        cursor.execute("SELECT employer_person_person_id FROM doctors WHERE employer_person_person_id = %s", (doctor_id,))
        if not cursor.fetchone():
            return jsonify({"status": StatusCodes['api_error'], "errors": "Doctor not found", "results": None}), StatusCodes['api_error']

        if not check_availability(patient_id, surgery_date, surgery_end):
            return jsonify({"status": StatusCodes['api_error'], "errors": "Patient has a conflict", "results": None}), StatusCodes['api_error']
        if not check_availability(doctor_id, surgery_date, surgery_end):
            return jsonify({"status": StatusCodes['api_error'], "errors": "Doctor has a conflict", "results": None}), StatusCodes['api_error']

        available_nurses = get_available_nurses(surgery_date, surgery_end)
        if len(available_nurses) < 5:
            return jsonify({"status": StatusCodes['api_error'], "errors": "Not enough nurses available", "results": None}), StatusCodes['api_error']

        cursor.execute(
            "INSERT INTO agenda (data_inicio, data_fim, employer_id, type, event_id) VALUES (%s, %s, %s, %s, NULL) RETURNING id_agenda",
            (surgery_date, surgery_end, doctor_id, 'surgery')
        )
        agenda_result = cursor.fetchone()
        if not agenda_result:
            return jsonify({"status": StatusCodes['internal_error'], "errors": "Failed to create agenda", "results": None}), StatusCodes['internal_error']
        
        agenda_id = agenda_result[0]
        nurse_id=available_nurses[0]
        cursor.execute(
            "INSERT INTO hospitalization (data_entrada, price, bill_bill_id, agenda_id_agenda, nurse_employer_person_person_id, pacient_person_person_id) VALUES (%s, 1500, NULL, %s, %s, %s) RETURNING hospitalization_id",
            (surgery_date, agenda_id,nurse_id,patient_id)
        )
        hospitalization_result = cursor.fetchone()
        if not hospitalization_result:
            return jsonify({"status": StatusCodes['internal_error'], "errors": "Failed to create hospitalization", "results": None}), StatusCodes['internal_error']
        
        hospitalization_id = hospitalization_result[0]


        cursor.execute(
            "INSERT INTO surgerie (surgerie_date, price, hospitalization_hospitalization_id, agenda_id_agenda, assistant_employer_person_person_id, doctors_employer_person_person_id, pacient_person_person_id) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING surgerie_id",
            (surgery_date, 700, hospitalization_id, agenda_id, user_id, doctor_id, patient_id)
        )
        surgerie_result = cursor.fetchone()
        if not surgerie_result:
            return jsonify({"status": StatusCodes['internal_error'], "errors": "Failed to create surgerie", "results": None}), StatusCodes['internal_error']
        
        surgery_id = surgerie_result[0]

        cursor.execute(
            "UPDATE agenda SET event_id = %s WHERE id_agenda = %s",
            (surgery_id, agenda_id)
        )

        for nurse_id in available_nurses[:5]:
            cursor.execute(
                "INSERT INTO nurse_surgerie (nurse_employer_person_person_id, surgerie_surgerie_id) VALUES (%s, %s)",
                (nurse_id, surgery_id)
            )
            cursor.execute(
                "INSERT INTO agenda (data_inicio, data_fim, employer_id, type, event_id) VALUES (%s, %s, %s, %s, %s)",
                (surgery_date, surgery_end, nurse_id, 'nurse_surgery', surgery_id)
            )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": StatusCodes['success'], "errors": None, "results": {"surgery_id": surgery_id, "patient_id": patient_id, "doctor_id": doctor_id, "date": surgery_date, "hospitalization_id": hospitalization_id}}), StatusCodes['success']

    except Exception as e:
        logging.error(f"Error scheduling surgery: {str(e)}")
        return jsonify({"status": StatusCodes['internal_error'], "errors": str(e), "results": None}), StatusCodes['internal_error']



@app.route('/dbproj/surgery/<int:hospitalization_id>', methods=['POST'])
@verify_token
def schedule_surgery_with_hospitalization(hospitalization_id):
    data = request.json
    patient_id = data.get('patient_id')
    doctor_id = data.get('doctor')
    surgery_date = datetime.datetime.strptime(data.get('date'), "%Y-%m-%dT%H:%M:%S")
    surgery_end = surgery_date + datetime.timedelta(hours=2)

    lock_id = 4

    try:
        acquire_lock(lock_id)
        
        conn = db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT person_id FROM person WHERE username = %s", (g.user,))
        user_result = cursor.fetchone()
        if not user_result:
            return jsonify({"status": StatusCodes['api_error'], "errors": "User not found", "results": None}), StatusCodes['api_error']
        
        user_id = user_result[0]
        cursor.execute("SELECT * FROM assistant WHERE employer_person_person_id = %s", (user_id,))
        if not cursor.fetchone():
            return jsonify({"status": StatusCodes['api_error'], "errors": "Only assistants can schedule surgeries", "results": None}), StatusCodes['api_error']

        cursor.execute("SELECT pacient_person_person_id FROM hospitalization WHERE hospitalization_id = %s", (hospitalization_id,))
        hospitalization_result = cursor.fetchone()
        if not hospitalization_result:
            return jsonify({"status": StatusCodes['api_error'], "errors": "Hospitalization not found", "results": None}), StatusCodes['api_error']
        associated_patient_id = hospitalization_result[0]

        if associated_patient_id != patient_id:
            return jsonify({"status": StatusCodes['api_error'], "errors": "Patient not associated with the given hospitalization", "results": None}), StatusCodes['api_error']

        cursor.execute("SELECT person_person_id FROM pacient WHERE person_person_id = %s", (patient_id,))
        if not cursor.fetchone():
            return jsonify({"status": StatusCodes['api_error'], "errors": "Patient not found", "results": None}), StatusCodes['api_error']

        cursor.execute("SELECT employer_person_person_id FROM doctors WHERE employer_person_person_id = %s", (doctor_id,))
        if not cursor.fetchone():
            return jsonify({"status": StatusCodes['api_error'], "errors": "Doctor not found", "results": None}), StatusCodes['api_error']

        if not check_availability(patient_id, surgery_date, surgery_end):
            return jsonify({"status": StatusCodes['api_error'], "errors": "Patient has a conflict", "results": None}), StatusCodes['api_error']
        if not check_availability(doctor_id, surgery_date, surgery_end):
            return jsonify({"status": StatusCodes['api_error'], "errors": "Doctor has a conflict", "results": None}), StatusCodes['api_error']
        available_nurses = get_available_nurses(surgery_date, surgery_end)
        if len(available_nurses) < 5:
            return jsonify({"status": StatusCodes['api_error'], "errors": "Not enough nurses available", "results": None}), StatusCodes['api_error']

        cursor.execute(
            "INSERT INTO agenda (data_inicio, data_fim, employer_id, type, event_id) VALUES (%s, %s, %s, %s, NULL) RETURNING id_agenda",
            (surgery_date, surgery_end, doctor_id, 'surgery')
        )
        agenda_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO surgerie (surgerie_date, price, hospitalization_hospitalization_id, agenda_id_agenda, assistant_employer_person_person_id, doctors_employer_person_person_id, pacient_person_person_id) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING surgerie_id",
            (surgery_date, 700, hospitalization_id, agenda_id, user_id, doctor_id, patient_id)
        )
        surgery_id = cursor.fetchone()[0]

        cursor.execute(
            "UPDATE agenda SET event_id = %s WHERE id_agenda = %s",
            (surgery_id, agenda_id)
        )

        cursor.execute(
            "UPDATE bill SET total_price = total_price + 700 WHERE bill_id = (SELECT bill_bill_id FROM hospitalization WHERE hospitalization_id = %s)",
            (hospitalization_id,)
        )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": StatusCodes['success'], "errors": None, "results": {"surgery_id": surgery_id, "patient_id": patient_id, "doctor_id": doctor_id, "date": surgery_date, "hospitalization_id": hospitalization_id}}), StatusCodes['success']
            
    except Exception as e:
        logging.error(f"Error scheduling surgery: {str(e)}")
        return jsonify({"status": StatusCodes['internal_error'], "errors": str(e), "results": None}), StatusCodes['internal_error']
    finally:
        release_lock(lock_id)



@app.route('/dbproj/prescription', methods=['POST'])
@verify_token
def add_prescription():
    data = request.json
    prescription_type = data.get('type')
    event_id = data.get('event_id')
    validity_date = datetime.datetime.strptime(data.get('validity'), "%Y-%m-%dT%H:%M:%S")
    medicines = data.get('medicines')

    lock_id = 5

    try:
        acquire_lock(lock_id)
        
        conn = db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT person_id FROM person WHERE username = %s", (g.user,))
        user_result = cursor.fetchone()
        if not user_result:
            return jsonify({"status": StatusCodes['api_error'], "errors": "User not found", "results": None}), StatusCodes['api_error']
        
        user_id = user_result[0]
        cursor.execute("SELECT * FROM doctors WHERE employer_person_person_id = %s", (user_id,))
        if not cursor.fetchone():
            return jsonify({"status": StatusCodes['api_error'], "errors": "Only doctors can add prescriptions", "results": None}), StatusCodes['api_error']

        cursor.execute(
            "INSERT INTO prescription (validity_date, type, medico_id) VALUES (%s, %s, %s) RETURNING prescription_id",
            (validity_date, prescription_type, user_id)
        )
        prescription_result = cursor.fetchone()
        if not prescription_result:
            return jsonify({"status": StatusCodes['internal_error'], "errors": "Failed to create prescription", "results": None}), StatusCodes['internal_erro']
        
        prescription_id = prescription_result[0]

        if prescription_type == 'appointment':
            cursor.execute(
                "INSERT INTO prescription_appointment (prescription_prescription_id, appointment_appointment_id) VALUES (%s, %s)",
                (prescription_id, event_id)
            )
        elif prescription_type == 'hospitalization':
            cursor.execute(
                "INSERT INTO hospitalization_prescription (hospitalization_hospitalization_id, prescription_prescription_id) VALUES (%s, %s)",
                (event_id, prescription_id)
            )
        else:
            return jsonify({"status": StatusCodes['api_error'], "errors": "Invalid prescription type", "results": None}), StatusCodes['api_error']

        for medicine in medicines:
            medicine_name = medicine.get('medicine')
            posology_dose = medicine.get('posology_dose')
            posology_frequency = medicine.get('posology_frequency')

            cursor.execute("SELECT medicine_id FROM medicine WHERE medicine_name = %s", (medicine_name,))
            medicine_result = cursor.fetchone()
            if not medicine_result:
                cursor.execute(
                    "INSERT INTO medicine (medicine_name) VALUES (%s) RETURNING medicine_id",
                    (medicine_name,)
                )
                medicine_result = cursor.fetchone()
                if not medicine_result:
                    return jsonify({"status": StatusCodes['internal_error'], "errors": "Failed to create medicine", "results": None}), StatusCodes['internal_error']
                medicine_id = medicine_result[0]
            else:
                medicine_id = medicine_result[0]

            cursor.execute(
                "INSERT INTO posology (prescription_id, medicine_id, dose, dose_frequency, medicine_medicine_id, prescription_prescription_id) VALUES (%s, %s, %s, %s, %s, %s)",
                (prescription_id, medicine_id, posology_dose, posology_frequency, medicine_id, prescription_id)
            )

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": StatusCodes['success'], "errors": None, "results": prescription_id}), StatusCodes['success']
    except Exception as e:
        logging.error(f"Error adding prescription: {str(e)}")
        return jsonify({"status": StatusCodes['internal_error'], "errors": str(e), "results": None}), StatusCodes['internal_error']
    finally:
        release_lock(lock_id)

@app.route('/dbproj/prescriptions/<int:person_id>', methods=['GET'])
@verify_token
def get_prescriptions(person_id):
    data = request.json
    token = data.get('token')
    
    try:
        conn = db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT person_id FROM person WHERE username = %s", (g.user,))
        user_result = cursor.fetchone()
        if not user_result:
            return jsonify({"status": StatusCodes['api_error'], "errors": "User not found", "results": None}), StatusCodes['api_error']
        
        user_id = user_result[0]
        cursor.execute("SELECT * FROM employer WHERE person_person_id = %s", (user_id,))
        is_employee = cursor.fetchone()

        if not is_employee and user_id != person_id:
            return jsonify({"status": StatusCodes['api_error'], "errors": "Only employees or the targeted patient can access this endpoint", "results": None}), StatusCodes['api_error']

        cursor.execute("""
            SELECT p.prescription_id, p.validity_date, p.type, po.dose, po.dose_frequency, m.medicine_name
            FROM prescription p
            LEFT JOIN posology po ON p.prescription_id = po.prescription_prescription_id
            LEFT JOIN medicine m ON po.medicine_medicine_id = m.medicine_id
            LEFT JOIN hospitalization_prescription hp ON p.prescription_id = hp.prescription_prescription_id
            LEFT JOIN prescription_appointment pa ON p.prescription_id = pa.prescription_prescription_id
            LEFT JOIN hospitalization h ON hp.hospitalization_hospitalization_id = h.hospitalization_id
            LEFT JOIN appointment a ON pa.appointment_appointment_id = a.appointment_id
            WHERE h.pacient_person_person_id = %s OR a.pacient_person_person_id = %s
            ORDER BY p.prescription_id
        """, (person_id, person_id))

        prescriptions = {}
        for row in cursor.fetchall():
            prescription_id, validity_date, prescription_type, dose, dose_frequency, medicine_name = row
            if prescription_id not in prescriptions:
                prescriptions[prescription_id] = {
                    "id": prescription_id,
                    "validity": validity_date,
                    "type": prescription_type,
                    "posology": []
                }
            prescriptions[prescription_id]["posology"].append({
                "dose": dose,
                "frequency": dose_frequency,
                "medicine": medicine_name
            })

        results = list(prescriptions.values())

        cursor.close()
        conn.close()

        return jsonify({"status": StatusCodes['success'], "errors": None, "results": results}), StatusCodes['success']

    except Exception as e:
        logging.error(f"Error fetching prescriptions: {str(e)}")
        return jsonify({"status": StatusCodes['internal_error'], "errors": str(e), "results": None}), StatusCodes['internal_error']

@app.route('/dbproj/bills/<int:bill_id>', methods=['POST'])
@verify_token
def execute_payment(bill_id):
    data = request.json
    amount = data.get('amount')
    payment_method = data.get('payment_method')

    lock_id = 6

    try:
        acquire_lock(lock_id)
        
        conn = db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT person_id FROM person WHERE username = %s", (g.user,))
        user_result = cursor.fetchone()
        if not user_result:
            return jsonify({"status": StatusCodes['api_error'], "errors": "User not found", "results": None}), StatusCodes['api_error']
        
        user_id = user_result[0]
        cursor.execute("SELECT * FROM pacient WHERE person_person_id = %s", (user_id,))
        if not cursor.fetchone():
            return jsonify({"status": StatusCodes['api_error'], "errors": "Only patients can pay bills", "results": None}), StatusCodes['api_error']

        cursor.execute("SELECT total_price FROM bill WHERE bill_id = %s AND pacient_person_person_id = %s", (bill_id, user_id))
        bill_result = cursor.fetchone()
        if not bill_result:
            return jsonify({"status": StatusCodes['not_found'], "errors": "Bill not found or does not belong to the patient", "results": None}), StatusCodes['not_found']
        
        total_price = bill_result[0]

        new_total_price = total_price - amount
        if new_total_price < 0:
            return jsonify({"status": StatusCodes['api_error'], "errors": "Payment amount exceeds total bill amount", "results": None}), StatusCodes['api_error']
        
        cursor.execute(
            "INSERT INTO payment (payment_method, amount, payment_date, bill_bill_id) VALUES (%s, %s, %s, %s) RETURNING payment_id",
            (payment_method, amount, datetime.datetime.now(), bill_id)
        )
        payment_id = cursor.fetchone()[0]

        cursor.execute(
            "UPDATE bill SET total_price = %s, status = %s WHERE bill_id = %s",
            (new_total_price, new_total_price == 0, bill_id)
        )

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": StatusCodes['success'], "errors": None, "results": {"remaining_value": new_total_price}}), StatusCodes['success']

    except Exception as e:
        logging.error(f"Error executing payment: {str(e)}")
        return jsonify({"status": StatusCodes['internal_error'], "errors": str(e), "results": None}), StatusCodes['internal_error']
    finally:
        release_lock(lock_id)

@app.route('/dbproj/top3', methods=['GET'])
@verify_token
def top3_patients():
    try:
        conn = db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT person_id FROM person WHERE username = %s", (g.user,))
        user_result = cursor.fetchone()
        if not user_result:
            return jsonify({"status": StatusCodes['api_error'], "errors": "User not found", "results": None}), StatusCodes['api_error']
        
        user_id = user_result[0]
        cursor.execute("SELECT * FROM assistant WHERE employer_person_person_id = %s", (user_id,))
        if not cursor.fetchone():
            return jsonify({"status": StatusCodes['api_error'], "errors": "Only assistants can view top patients", "results": None}), StatusCodes['api_error']

        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month

        query = """
        SELECT
            p.username AS patient_username,
            p.name AS patient_name,
            SUM(py.amount) AS amount_spent,
            json_agg(json_build_object(
                'id', CASE
                          WHEN a.appointment_id IS NOT NULL THEN a.appointment_id
                          WHEN h.hospitalization_id IS NOT NULL THEN h.hospitalization_id
                          WHEN s.surgerie_id IS NOT NULL THEN s.surgerie_id
                      END,
                'date', COALESCE(a.appointment_date, h.data_entrada, s.surgerie_date)
            )) AS procedures
        FROM
            payment py
        JOIN
            bill b ON py.bill_bill_id = b.bill_id
        JOIN
            person p ON b.pacient_person_person_id = p.person_id
        LEFT JOIN
            appointment a ON b.bill_id = a.bill_bill_id
        LEFT JOIN
            hospitalization h ON b.bill_id = h.bill_bill_id
        LEFT JOIN
            surgerie s ON h.hospitalization_id = s.hospitalization_hospitalization_id
        WHERE
            EXTRACT(YEAR FROM py.payment_date) = %s AND
            EXTRACT(MONTH FROM py.payment_date) = %s
        GROUP BY
            p.username, p.name
        ORDER BY
            amount_spent DESC
        LIMIT 3;
        """
        cursor.execute(query, (current_year, current_month))
        top3_results = cursor.fetchall()

        results = []
        for row in top3_results:
            patient_username = row[0]
            patient_name = row[1]
            amount_spent = row[2]
            procedures = row[3]
            results.append({
                "patient_username": patient_username,
                "patient_name": patient_name,
                "amount_spent": amount_spent,
                "procedures": procedures
            })

        conn.close()

        return jsonify({"status": StatusCodes['success'], "errors": None, "results": results}), StatusCodes['success']

    except Exception as e:
        logging.error(f"Error getting top 3 patients: {str(e)}")
        return jsonify({"status": StatusCodes['internal_error'], "errors": str(e), "results": None}), StatusCodes['internal_error']


@app.route('/dbproj/daily/<string:date>', methods=['GET'])
@verify_token
def daily_summary(date):
    try:
        conn = db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT person_id FROM person WHERE username = %s", (g.user,))
        user_result = cursor.fetchone()
        if not user_result:
            return jsonify({"status": StatusCodes['api_error'], "errors": "User not found", "results": None}), StatusCodes['api_error']
        
        user_id = user_result[0]
        cursor.execute("SELECT * FROM assistant WHERE employer_person_person_id = %s", (user_id,))
        if not cursor.fetchone():
            return jsonify({"status": StatusCodes['api_error'], "errors": "Only assistants can view the daily summary", "results": None}), StatusCodes['api_error']

        query = """
        SELECT
            COALESCE(SUM(py.amount), 0) AS amount_spent,
            COALESCE(COUNT(DISTINCT s.surgerie_id), 0) AS surgeries,
            COALESCE(COUNT(DISTINCT pr.prescription_id), 0) AS prescriptions
        FROM
            bill b
        LEFT JOIN
            payment py ON b.bill_id = py.bill_bill_id
        LEFT JOIN
            hospitalization h ON b.bill_id = h.bill_bill_id
        LEFT JOIN
            surgerie s ON h.hospitalization_id = s.hospitalization_hospitalization_id
        LEFT JOIN
            hospitalization_prescription hp ON h.hospitalization_id = hp.hospitalization_hospitalization_id
        LEFT JOIN
            prescription pr ON hp.prescription_prescription_id = pr.prescription_id
        WHERE
            py.payment_date::date = %s
            OR s.surgerie_date::date = %s
            OR pr.validity_date::date = %s
        """
        
        cursor.execute(query, (date, date, date))
        result = cursor.fetchone()
        
        daily_summary = {
            "amount_spent": result[0],
            "surgeries": result[1],
            "prescriptions": result[2]
        }

        conn.close()

        return jsonify({"status": StatusCodes['success'], "errors": None, "results": daily_summary}), StatusCodes['success']

    except Exception as e:
        logging.error(f"Error getting daily summary: {str(e)}")
        return jsonify({"status": StatusCodes['internal_error'], "errors": str(e), "results": None}), StatusCodes['internal_error']

@app.route('/dbproj/report', methods=['GET'])
@verify_token
def monthly_report():
    try:
        conn = db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT person_id FROM person WHERE username = %s", (g.user,))
        user_result = cursor.fetchone()
        if not user_result:
            return jsonify({"status": StatusCodes['api_error'], "errors": "User not found", "results": None}), StatusCodes['api_error']
        
        user_id = user_result[0]
        cursor.execute("SELECT * FROM assistant WHERE employer_person_person_id = %s", (user_id,))
        if not cursor.fetchone():
            return jsonify({"status": StatusCodes['api_error'], "errors": "Only assistants can view the report", "results": None}), StatusCodes['api_error']

        query = """
        WITH doctor_surgeries AS (
            SELECT
                TO_CHAR(s.surgerie_date, 'YYYY-MM') AS month,
                p.name AS doctor,
                COUNT(s.surgerie_id) AS surgeries
            FROM
                surgerie s
            JOIN
                doctors d ON s.doctors_employer_person_person_id = d.employer_person_person_id
            JOIN
                person p ON d.employer_person_person_id = p.person_id
            WHERE
                s.surgerie_date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '12 months'
            GROUP BY
                TO_CHAR(s.surgerie_date, 'YYYY-MM'),
                p.name
        ),
        ranked_surgeries AS (
            SELECT
                month,
                doctor,
                surgeries,
                ROW_NUMBER() OVER (PARTITION BY month ORDER BY surgeries DESC) AS rank
            FROM
                doctor_surgeries
        )
        SELECT
            month,
            doctor,
            surgeries
        FROM
            ranked_surgeries
        WHERE
            rank = 1
        ORDER BY
            month DESC;
        """

        cursor.execute(query)
        result = cursor.fetchall()

        monthly_report = []
        for row in result:
            monthly_report.append({
                "month": row[0],
                "doctor": row[1],
                "surgeries": row[2]
            })

        conn.close()

        return jsonify({"status": StatusCodes['success'], "errors": None, "results": monthly_report}), StatusCodes['success']
    except Exception as e:
        logging.error(f"Error getting monthly report: {str(e)}")
        return jsonify({"status": StatusCodes['internal_error'], "errors": str(e), "results": None}), StatusCodes['internal_error']



if __name__ == '__main__':
    host = '127.0.0.1'
    port = 8080
    app.run(host=host, debug=True, threaded=True, port=port)
