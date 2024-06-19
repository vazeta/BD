CREATE OR REPLACE FUNCTION create_bill_before_appointment() 
RETURNS TRIGGER AS $$
DECLARE
    new_bill_id BIGINT;
BEGIN
    INSERT INTO bill (data_expira, date_inicio, status, total_price, pacient_person_person_id)
    VALUES (CURRENT_TIMESTAMP + interval '30 days', CURRENT_TIMESTAMP, FALSE, NEW.price, NEW.pacient_person_person_id)
    RETURNING bill_id INTO new_bill_id;

    NEW.bill_bill_id = new_bill_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TRIGGER trigger_create_bill_before_appointment
BEFORE INSERT ON appointment
FOR EACH ROW
EXECUTE FUNCTION create_bill_before_appointment();



CREATE OR REPLACE FUNCTION manage_hospitalization_bill() RETURNS TRIGGER AS $$
DECLARE
    new_bill_id BIGINT;
BEGIN
    IF NEW.bill_bill_id IS NULL THEN
        INSERT INTO bill (data_expira, date_inicio, status, total_price, pacient_person_person_id)
        VALUES (CURRENT_TIMESTAMP + interval '30 days', CURRENT_TIMESTAMP, FALSE, 1500, NEW.pacient_person_person_id)
        RETURNING bill_id INTO new_bill_id;
        NEW.bill_bill_id = new_bill_id;
    ELSE
        UPDATE bill
        SET total_price = total_price + 1500
        WHERE bill_id = NEW.bill_bill_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_manage_hospitalization_bill ON hospitalization;

CREATE TRIGGER trigger_manage_hospitalization_bill
BEFORE INSERT ON hospitalization
FOR EACH ROW
EXECUTE FUNCTION manage_hospitalization_bill();
