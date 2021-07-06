--
-- PostgreSQL database dump
--

-- Dumped from database version 9.6.17
-- Dumped by pg_dump version 9.6.17

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


--
-- Name: tf_sensors_data_bi(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.tf_sensors_data_bi() RETURNS trigger
    LANGUAGE plpgsql
    AS $$declare
	correction numeric;
begin
	select sensors.correction from sensors where id = new.sensor_id and sensors.correction is not null into correction;
	if found then
		new.value = new.value + correction;
	end if;
	return new;
end;
	$$;


ALTER FUNCTION public.tf_sensors_data_bi() OWNER TO postgres;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: device_schedule_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.device_schedule_items (
    schedule_id integer NOT NULL,
    day_no smallint NOT NULL,
    params jsonb
);


ALTER TABLE public.device_schedule_items OWNER TO postgres;

--
-- Name: device_schedules; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.device_schedules (
    id integer NOT NULL,
    login character varying(16),
    title character varying(64),
    device_type_id integer NOT NULL,
    hash character varying(64),
    params jsonb
);


ALTER TABLE public.device_schedules OWNER TO postgres;

--
-- Name: device_schedules_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.device_schedules_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.device_schedules_id_seq OWNER TO postgres;

--
-- Name: device_schedules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.device_schedules_id_seq OWNED BY public.device_schedules.id;


--
-- Name: device_type_sensors; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.device_type_sensors (
    device_type_id smallint NOT NULL,
    id integer NOT NULL,
    sensor_type character varying(64) NOT NULL,
    title character varying(64) NOT NULL,
    is_master boolean DEFAULT false
);


ALTER TABLE public.device_type_sensors OWNER TO postgres;

--
-- Name: device_type_sensors_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.device_type_sensors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.device_type_sensors_id_seq OWNER TO postgres;

--
-- Name: device_type_sensors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.device_type_sensors_id_seq OWNED BY public.device_type_sensors.id;


--
-- Name: device_type_switches; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.device_type_switches (
    id smallint NOT NULL,
    device_type_id smallint NOT NULL,
    title character varying(64) NOT NULL,
    type character varying(16)
);


ALTER TABLE public.device_type_switches OWNER TO postgres;

--
-- Name: device_type_switches_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.device_type_switches_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.device_type_switches_id_seq OWNER TO postgres;

--
-- Name: device_type_switches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.device_type_switches_id_seq OWNED BY public.device_type_switches.id;


--
-- Name: devices; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.devices (
    id integer NOT NULL,
    device_type_id smallint NOT NULL,
    title character varying(64),
    login character varying(32),
    local_title character varying(32),
    props jsonb,
    schedule_id integer,
    last_contact timestamp without time zone,
    public_access boolean DEFAULT false NOT NULL,
    mode character varying(64)
);


ALTER TABLE public.devices OWNER TO postgres;

--
-- Name: devices_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.devices_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.devices_id_seq OWNER TO postgres;

--
-- Name: devices_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.devices_id_seq OWNED BY public.devices.id;


--
-- Name: devices_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.devices_log (
    id integer NOT NULL,
    log_tstamp timestamp without time zone NOT NULL,
    device_id integer NOT NULL,
    rcvd_tstamp timestamp without time zone DEFAULT now() NOT NULL,
    txt character varying(512) NOT NULL
);


ALTER TABLE public.devices_log OWNER TO postgres;

--
-- Name: devices_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.devices_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.devices_log_id_seq OWNER TO postgres;

--
-- Name: devices_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.devices_log_id_seq OWNED BY public.devices_log.id;


--
-- Name: devices_switches; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.devices_switches (
    device_id integer NOT NULL,
    device_type_switch_id smallint NOT NULL,
    title character varying(64),
    enabled boolean DEFAULT false NOT NULL
);


ALTER TABLE public.devices_switches OWNER TO postgres;

--
-- Name: devices_switches_state; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.devices_switches_state (
    tstamp timestamp without time zone NOT NULL,
    device_id integer NOT NULL,
    device_type_switch_id smallint NOT NULL,
    state boolean NOT NULL
);


ALTER TABLE public.devices_switches_state OWNER TO postgres;

--
-- Name: devices_types; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.devices_types (
    id integer NOT NULL,
    title character varying(64) NOT NULL,
    props jsonb,
    schedule_params jsonb,
    rtc boolean DEFAULT true NOT NULL,
    software_type character varying(32),
    updates boolean DEFAULT true,
    modes jsonb
);


ALTER TABLE public.devices_types OWNER TO postgres;

--
-- Name: devices_types_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.devices_types_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.devices_types_id_seq OWNER TO postgres;

--
-- Name: devices_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.devices_types_id_seq OWNED BY public.devices_types.id;


--
-- Name: sensors; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sensors (
    id integer NOT NULL,
    device_type_sensor_id smallint NOT NULL,
    title character varying(64),
    device_id integer NOT NULL,
    is_master boolean DEFAULT false,
    enabled boolean DEFAULT true,
    correction numeric(8,2)
);


ALTER TABLE public.sensors OWNER TO postgres;

--
-- Name: sensors_data; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sensors_data (
    tstamp timestamp without time zone DEFAULT now() NOT NULL,
    sensor_id integer NOT NULL,
    value numeric(8,2)
);


ALTER TABLE public.sensors_data OWNER TO postgres;

--
-- Name: sensors_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.sensors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.sensors_id_seq OWNER TO postgres;

--
-- Name: sensors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.sensors_id_seq OWNED BY public.sensors.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    login character varying(16) NOT NULL,
    password character varying(64) NOT NULL,
    public_id character varying(64),
    timezone character varying(64) DEFAULT 'Europe/Moscow'::character varying NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: device_schedules id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device_schedules ALTER COLUMN id SET DEFAULT nextval('public.device_schedules_id_seq'::regclass);


--
-- Name: device_type_sensors id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device_type_sensors ALTER COLUMN id SET DEFAULT nextval('public.device_type_sensors_id_seq'::regclass);


--
-- Name: device_type_switches id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device_type_switches ALTER COLUMN id SET DEFAULT nextval('public.device_type_switches_id_seq'::regclass);


--
-- Name: devices id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices ALTER COLUMN id SET DEFAULT nextval('public.devices_id_seq'::regclass);


--
-- Name: devices_log id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices_log ALTER COLUMN id SET DEFAULT nextval('public.devices_log_id_seq'::regclass);


--
-- Name: devices_types id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices_types ALTER COLUMN id SET DEFAULT nextval('public.devices_types_id_seq'::regclass);


--
-- Name: sensors id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sensors ALTER COLUMN id SET DEFAULT nextval('public.sensors_id_seq'::regclass);


--
-- Name: device_schedule_items device_schedule_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device_schedule_items
    ADD CONSTRAINT device_schedule_items_pkey PRIMARY KEY (schedule_id, day_no);


--
-- Name: device_schedules device_schedules_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device_schedules
    ADD CONSTRAINT device_schedules_pkey PRIMARY KEY (id);


--
-- Name: device_type_sensors device_type_sensors_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device_type_sensors
    ADD CONSTRAINT device_type_sensors_pkey PRIMARY KEY (id);


--
-- Name: device_type_switches device_type_switches_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device_type_switches
    ADD CONSTRAINT device_type_switches_pkey PRIMARY KEY (id);


--
-- Name: devices_log devices_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices_log
    ADD CONSTRAINT devices_log_pkey PRIMARY KEY (id);


--
-- Name: devices devices_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_pkey PRIMARY KEY (id);


--
-- Name: devices_switches devices_switches_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices_switches
    ADD CONSTRAINT devices_switches_pkey PRIMARY KEY (device_id, device_type_switch_id);


--
-- Name: devices_switches_state devices_switches_state_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices_switches_state
    ADD CONSTRAINT devices_switches_state_pkey PRIMARY KEY (tstamp, device_id, device_type_switch_id);


--
-- Name: devices_switches_state devices_switches_state_tstamp_check; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE public.devices_switches_state
    ADD CONSTRAINT devices_switches_state_tstamp_check CHECK ((tstamp < (now() + '1 day'::interval))) NOT VALID;


--
-- Name: devices_types devices_types_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices_types
    ADD CONSTRAINT devices_types_pkey PRIMARY KEY (id);


--
-- Name: sensors_data sensors_data_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sensors_data
    ADD CONSTRAINT sensors_data_pkey PRIMARY KEY (sensor_id, tstamp);


--
-- Name: sensors_data sensors_data_tstamp_check; Type: CHECK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE public.sensors_data
    ADD CONSTRAINT sensors_data_tstamp_check CHECK ((tstamp < (now() + '1 day'::interval))) NOT VALID;


--
-- Name: sensors sensors_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sensors
    ADD CONSTRAINT sensors_pkey PRIMARY KEY (id);


--
-- Name: users users_pk; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pk PRIMARY KEY (login);


--
-- Name: devices_schedules_fkey; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX devices_schedules_fkey ON public.devices USING btree (schedule_id);


--
-- Name: sensors_data tr_sensor_data_bi; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER tr_sensor_data_bi BEFORE INSERT ON public.sensors_data FOR EACH ROW EXECUTE PROCEDURE public.tf_sensors_data_bi();


--
-- Name: device_schedule_items device_schedule_items_schedule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device_schedule_items
    ADD CONSTRAINT device_schedule_items_schedule_id_fkey FOREIGN KEY (schedule_id) REFERENCES public.device_schedules(id);


--
-- Name: device_schedules device_schedules_device_type_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device_schedules
    ADD CONSTRAINT device_schedules_device_type_fkey FOREIGN KEY (device_type_id) REFERENCES public.devices_types(id);


--
-- Name: device_schedules device_schedules_login_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device_schedules
    ADD CONSTRAINT device_schedules_login_fkey FOREIGN KEY (login) REFERENCES public.users(login);


--
-- Name: device_type_sensors device_type_sensors_device_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device_type_sensors
    ADD CONSTRAINT device_type_sensors_device_type_id_fkey FOREIGN KEY (device_type_id) REFERENCES public.devices_types(id) NOT VALID;


--
-- Name: device_type_switches device_type_switches_device_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device_type_switches
    ADD CONSTRAINT device_type_switches_device_type_id_fkey FOREIGN KEY (device_type_id) REFERENCES public.devices_types(id);


--
-- Name: devices devices_device_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_device_type_id_fkey FOREIGN KEY (device_type_id) REFERENCES public.devices_types(id);


--
-- Name: devices_log devices_log_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices_log
    ADD CONSTRAINT devices_log_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(id);


--
-- Name: devices devices_schedule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_schedule_id_fkey FOREIGN KEY (schedule_id) REFERENCES public.device_schedules(id) NOT VALID;


--
-- Name: devices_switches_state devices_switches_state_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices_switches_state
    ADD CONSTRAINT devices_switches_state_device_id_fkey FOREIGN KEY (device_id, device_type_switch_id) REFERENCES public.devices_switches(device_id, device_type_switch_id);


--
-- Name: devices devices_user_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_user_fkey FOREIGN KEY (login) REFERENCES public.users(login) NOT VALID;


--
-- Name: sensors_data sensors_data_sensor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sensors_data
    ADD CONSTRAINT sensors_data_sensor_id_fkey FOREIGN KEY (sensor_id) REFERENCES public.sensors(id);


--
-- Name: sensors sensors_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sensors
    ADD CONSTRAINT sensors_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(id) NOT VALID;


--
-- Name: FUNCTION tf_sensors_data_bi(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.tf_sensors_data_bi() TO "www-group";


--
-- Name: TABLE device_schedule_items; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.device_schedule_items TO "www-group";


--
-- Name: TABLE device_schedules; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.device_schedules TO "www-group";


--
-- Name: SEQUENCE device_schedules_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.device_schedules_id_seq TO "www-group";


--
-- Name: TABLE device_type_sensors; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,UPDATE ON TABLE public.device_type_sensors TO "www-group";


--
-- Name: TABLE device_type_switches; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,REFERENCES ON TABLE public.device_type_switches TO "www-group";


--
-- Name: TABLE devices; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,REFERENCES,DELETE,UPDATE ON TABLE public.devices TO "www-group";


--
-- Name: SEQUENCE devices_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.devices_id_seq TO "www-group";


--
-- Name: TABLE devices_log; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,TRUNCATE,UPDATE ON TABLE public.devices_log TO "www-group";


--
-- Name: SEQUENCE devices_log_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.devices_log_id_seq TO "www-group";


--
-- Name: TABLE devices_switches; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,REFERENCES,TRIGGER,UPDATE ON TABLE public.devices_switches TO "www-group";


--
-- Name: TABLE devices_switches_state; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,UPDATE ON TABLE public.devices_switches_state TO "www-group";


--
-- Name: TABLE devices_types; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT ON TABLE public.devices_types TO "www-group";


--
-- Name: TABLE sensors; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,UPDATE ON TABLE public.sensors TO "www-group";


--
-- Name: TABLE sensors_data; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,REFERENCES,DELETE,UPDATE ON TABLE public.sensors_data TO "www-group";


--
-- Name: SEQUENCE sensors_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.sensors_id_seq TO "www-group";


--
-- Name: TABLE users; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.users TO "www-group";


--
-- PostgreSQL database dump complete
--

