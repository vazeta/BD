CREATE TABLE person (
	person_id SERIAL,
	name	 VARCHAR(512) NOT NULL,
	email	 VARCHAR(512) NOT NULL,
	username	 VARCHAR(512) NOT NULL,
	password	 VARCHAR(512) NOT NULL,
	PRIMARY KEY(person_id)
);

CREATE TABLE pacient (
	person_person_id INTEGER,
	PRIMARY KEY(person_person_id)
);

CREATE TABLE employer (
	contract_details TEXT NOT NULL,
	person_person_id INTEGER,
	PRIMARY KEY(person_person_id)
);

CREATE TABLE doctors (
	specialization		 VARCHAR(512) NOT NULL,
	employer_person_person_id INTEGER,
	PRIMARY KEY(employer_person_person_id)
);

CREATE TABLE assistant (
	employer_person_person_id INTEGER,
	PRIMARY KEY(employer_person_person_id)
);

CREATE TABLE medical_license (
	doctor_name			 VARCHAR(512) NOT NULL,
	license_id			 INTEGER NOT NULL,
	expiration_date			 TIMESTAMP NOT NULL,
	doctors_employer_person_person_id INTEGER,
	PRIMARY KEY(doctors_employer_person_person_id)
);

CREATE TABLE nurse (
	hierarchy		 VARCHAR(512) NOT NULL,
	employer_person_person_id INTEGER,
	PRIMARY KEY(employer_person_person_id)
);

CREATE TABLE surgerie (
	surgerie_id			 BIGSERIAL,
	surgerie_date			 TIMESTAMP NOT NULL,
	price				 BIGINT NOT NULL DEFAULT 700,
	hospitalization_hospitalization_id	 BIGINT NOT NULL,
	agenda_id_agenda			 INTEGER NOT NULL,
	assistant_employer_person_person_id INTEGER NOT NULL,
	doctors_employer_person_person_id	 INTEGER NOT NULL,
	pacient_person_person_id		 INTEGER NOT NULL,
	PRIMARY KEY(surgerie_id)
);

CREATE TABLE hospitalization (
	hospitalization_id		 BIGSERIAL,
	data_entrada			 TIMESTAMP NOT NULL,
	price				 BIGINT NOT NULL DEFAULT 15,
	bill_bill_id			 BIGINT NOT NULL,
	agenda_id_agenda		 INTEGER NOT NULL,
	nurse_employer_person_person_id INTEGER NOT NULL,
	pacient_person_person_id	 INTEGER NOT NULL,
	PRIMARY KEY(hospitalization_id)
);

CREATE TABLE appointment (
	appointment_id			 BIGSERIAL,
	appointment_date			 TIMESTAMP NOT NULL,
	pacient_id			 BIGINT NOT NULL,
	price				 BIGINT NOT NULL DEFAULT 40,
	agenda_id_agenda			 INTEGER NOT NULL,
	bill_bill_id			 BIGINT NOT NULL,
	pacient_person_person_id		 INTEGER NOT NULL,
	doctors_employer_person_person_id INTEGER NOT NULL,
	PRIMARY KEY(appointment_id)
);

CREATE TABLE bill (
	bill_id			 BIGSERIAL,
	data_expira		 TIMESTAMP NOT NULL,
	date_inicio		 TIMESTAMP NOT NULL,
	status			 BOOL NOT NULL,
	total_price		 BIGINT NOT NULL,
	pacient_person_person_id INTEGER NOT NULL,
	PRIMARY KEY(bill_id)
);

CREATE TABLE payment (
	payment_id	 BIGSERIAL,
	payment_method VARCHAR(512) NOT NULL,
	amount	 BIGINT NOT NULL,
	payment_date	 TIMESTAMP NOT NULL,
	bill_bill_id	 BIGINT NOT NULL,
	PRIMARY KEY(payment_id)
);

CREATE TABLE prescription (
	prescription_id BIGSERIAL,
	validity_date	 TIMESTAMP NOT NULL,
	type		 VARCHAR(512) NOT NULL,
	medico_id	 BIGINT NOT NULL,
	PRIMARY KEY(prescription_id)
);

CREATE TABLE medicine (
	medicine_id	 BIGSERIAL,
	medicine_name VARCHAR(512) NOT NULL,
	PRIMARY KEY(medicine_id)
);

CREATE TABLE posology (
	posology_id			 BIGSERIAL,
	prescription_id		 BIGINT NOT NULL,
	medicine_id			 BIGINT NOT NULL,
	dose			 BIGINT NOT NULL,
	dose_frequency		 VARCHAR(512) NOT NULL,
	medicine_medicine_id	 BIGINT NOT NULL,
	prescription_prescription_id BIGINT NOT NULL,
	PRIMARY KEY(posology_id)
);

CREATE TABLE side_effect (
	side_effect_id BIGSERIAL,
	description	 TEXT NOT NULL,
	ocurrency	 VARCHAR(512) NOT NULL,
	severity	 VARCHAR(512) NOT NULL,
	PRIMARY KEY(side_effect_id)
);

CREATE TABLE agenda (
	id_agenda	 SERIAL,
	data_inicio TIMESTAMP NOT NULL,
	data_fim	 TIMESTAMP NOT NULL,
	employer_id BIGINT NOT NULL,
	type	 VARCHAR(512) NOT NULL,
	event_id	 BIGINT,
	PRIMARY KEY(id_agenda)
);

CREATE TABLE side_effect_medicine (
	side_effect_side_effect_id BIGINT,
	medicine_medicine_id	 BIGINT,
	PRIMARY KEY(side_effect_side_effect_id,medicine_medicine_id)
);

CREATE TABLE nurse_appointment (
	nurse_employer_person_person_id INTEGER,
	appointment_appointment_id	 BIGINT NOT NULL,
	PRIMARY KEY(nurse_employer_person_person_id)
);

CREATE TABLE nurse_surgerie (
	nurse_employer_person_person_id INTEGER,
	surgerie_surgerie_id		 BIGINT,
	PRIMARY KEY(nurse_employer_person_person_id,surgerie_surgerie_id)
);

CREATE TABLE hospitalization_prescription (
	hospitalization_hospitalization_id BIGINT NOT NULL,
	prescription_prescription_id	 BIGINT,
	PRIMARY KEY(prescription_prescription_id)
);

CREATE TABLE prescription_appointment (
	prescription_prescription_id BIGINT,
	appointment_appointment_id	 BIGINT NOT NULL,
	PRIMARY KEY(prescription_prescription_id)
);

ALTER TABLE person ADD UNIQUE (email, username);
ALTER TABLE pacient ADD CONSTRAINT pacient_fk1 FOREIGN KEY (person_person_id) REFERENCES person(person_id);
ALTER TABLE employer ADD UNIQUE (contract_details);
ALTER TABLE employer ADD CONSTRAINT employer_fk1 FOREIGN KEY (person_person_id) REFERENCES person(person_id);
ALTER TABLE doctors ADD CONSTRAINT doctors_fk1 FOREIGN KEY (employer_person_person_id) REFERENCES employer(person_person_id);
ALTER TABLE assistant ADD CONSTRAINT assistant_fk1 FOREIGN KEY (employer_person_person_id) REFERENCES employer(person_person_id);
ALTER TABLE medical_license ADD UNIQUE (license_id);
ALTER TABLE medical_license ADD CONSTRAINT medical_license_fk1 FOREIGN KEY (doctors_employer_person_person_id) REFERENCES doctors(employer_person_person_id);
ALTER TABLE nurse ADD CONSTRAINT nurse_fk1 FOREIGN KEY (employer_person_person_id) REFERENCES employer(person_person_id);
ALTER TABLE surgerie ADD CONSTRAINT surgerie_fk1 FOREIGN KEY (hospitalization_hospitalization_id) REFERENCES hospitalization(hospitalization_id);
ALTER TABLE surgerie ADD CONSTRAINT surgerie_fk2 FOREIGN KEY (agenda_id_agenda) REFERENCES agenda(id_agenda);
ALTER TABLE surgerie ADD CONSTRAINT surgerie_fk3 FOREIGN KEY (assistant_employer_person_person_id) REFERENCES assistant(employer_person_person_id);
ALTER TABLE surgerie ADD CONSTRAINT surgerie_fk4 FOREIGN KEY (doctors_employer_person_person_id) REFERENCES doctors(employer_person_person_id);
ALTER TABLE surgerie ADD CONSTRAINT surgerie_fk5 FOREIGN KEY (pacient_person_person_id) REFERENCES pacient(person_person_id);
ALTER TABLE hospitalization ADD CONSTRAINT hospitalization_fk1 FOREIGN KEY (bill_bill_id) REFERENCES bill(bill_id);
ALTER TABLE hospitalization ADD CONSTRAINT hospitalization_fk2 FOREIGN KEY (agenda_id_agenda) REFERENCES agenda(id_agenda);
ALTER TABLE hospitalization ADD CONSTRAINT hospitalization_fk3 FOREIGN KEY (nurse_employer_person_person_id) REFERENCES nurse(employer_person_person_id);
ALTER TABLE hospitalization ADD CONSTRAINT hospitalization_fk4 FOREIGN KEY (pacient_person_person_id) REFERENCES pacient(person_person_id);
ALTER TABLE appointment ADD UNIQUE (bill_bill_id);
ALTER TABLE appointment ADD CONSTRAINT appointment_fk1 FOREIGN KEY (agenda_id_agenda) REFERENCES agenda(id_agenda);
ALTER TABLE appointment ADD CONSTRAINT appointment_fk2 FOREIGN KEY (bill_bill_id) REFERENCES bill(bill_id);
ALTER TABLE appointment ADD CONSTRAINT appointment_fk3 FOREIGN KEY (pacient_person_person_id) REFERENCES pacient(person_person_id);
ALTER TABLE appointment ADD CONSTRAINT appointment_fk4 FOREIGN KEY (doctors_employer_person_person_id) REFERENCES doctors(employer_person_person_id);
ALTER TABLE bill ADD CONSTRAINT bill_fk1 FOREIGN KEY (pacient_person_person_id) REFERENCES pacient(person_person_id);
ALTER TABLE payment ADD CONSTRAINT payment_fk1 FOREIGN KEY (bill_bill_id) REFERENCES bill(bill_id);
ALTER TABLE posology ADD CONSTRAINT posology_fk1 FOREIGN KEY (medicine_medicine_id) REFERENCES medicine(medicine_id);
ALTER TABLE posology ADD CONSTRAINT posology_fk2 FOREIGN KEY (prescription_prescription_id) REFERENCES prescription(prescription_id);
ALTER TABLE side_effect_medicine ADD CONSTRAINT side_effect_medicine_fk1 FOREIGN KEY (side_effect_side_effect_id) REFERENCES side_effect(side_effect_id);
ALTER TABLE side_effect_medicine ADD CONSTRAINT side_effect_medicine_fk2 FOREIGN KEY (medicine_medicine_id) REFERENCES medicine(medicine_id);
ALTER TABLE nurse_appointment ADD CONSTRAINT nurse_appointment_fk1 FOREIGN KEY (nurse_employer_person_person_id) REFERENCES nurse(employer_person_person_id);
ALTER TABLE nurse_appointment ADD CONSTRAINT nurse_appointment_fk2 FOREIGN KEY (appointment_appointment_id) REFERENCES appointment(appointment_id);
ALTER TABLE nurse_surgerie ADD CONSTRAINT nurse_surgerie_fk1 FOREIGN KEY (nurse_employer_person_person_id) REFERENCES nurse(employer_person_person_id);
ALTER TABLE nurse_surgerie ADD CONSTRAINT nurse_surgerie_fk2 FOREIGN KEY (surgerie_surgerie_id) REFERENCES surgerie(surgerie_id);
ALTER TABLE hospitalization_prescription ADD CONSTRAINT hospitalization_prescription_fk1 FOREIGN KEY (hospitalization_hospitalization_id) REFERENCES hospitalization(hospitalization_id);
ALTER TABLE hospitalization_prescription ADD CONSTRAINT hospitalization_prescription_fk2 FOREIGN KEY (prescription_prescription_id) REFERENCES prescription(prescription_id);
ALTER TABLE prescription_appointment ADD CONSTRAINT prescription_appointment_fk1 FOREIGN KEY (prescription_prescription_id) REFERENCES prescription(prescription_id);
ALTER TABLE prescription_appointment ADD CONSTRAINT prescription_appointment_fk2 FOREIGN KEY (appointment_appointment_id) REFERENCES appointment(appointment_id);
