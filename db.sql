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


SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: device_type_sensors; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.device_type_sensors (
    device_type_id smallint NOT NULL,
    id integer NOT NULL,
    sensor_type character varying(64) NOT NULL,
    title character varying(64) NOT NULL
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
-- Name: devices; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.devices (
    id integer NOT NULL,
    device_type_id smallint NOT NULL,
    title character varying(64) NOT NULL,
    "user" character varying(32) NOT NULL
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
-- Name: devices_types; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.devices_types (
    id integer NOT NULL,
    title character varying(64) NOT NULL
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
    title character varying(64) NOT NULL,
    device_id integer NOT NULL
);


ALTER TABLE public.sensors OWNER TO postgres;

--
-- Name: sensors_data; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sensors_data (
    tstamp timestamp without time zone NOT NULL,
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
    email character varying(64)
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: device_type_sensors id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device_type_sensors ALTER COLUMN id SET DEFAULT nextval('public.device_type_sensors_id_seq'::regclass);


--
-- Name: devices id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices ALTER COLUMN id SET DEFAULT nextval('public.devices_id_seq'::regclass);


--
-- Name: devices_types id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices_types ALTER COLUMN id SET DEFAULT nextval('public.devices_types_id_seq'::regclass);


--
-- Name: sensors id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sensors ALTER COLUMN id SET DEFAULT nextval('public.sensors_id_seq'::regclass);


--
-- Name: device_type_sensors device_type_sensors_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device_type_sensors
    ADD CONSTRAINT device_type_sensors_pkey PRIMARY KEY (id);


--
-- Name: devices devices_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_pkey PRIMARY KEY (id);


--
-- Name: devices_types devices_types_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices_types
    ADD CONSTRAINT devices_types_pkey PRIMARY KEY (id);


--
-- Name: sensors_data sensors_data_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sensors_data
    ADD CONSTRAINT sensors_data_pkey PRIMARY KEY (tstamp, sensor_id);


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
-- Name: device_type_sensors device_type_sensors_device_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.device_type_sensors
    ADD CONSTRAINT device_type_sensors_device_type_id_fkey FOREIGN KEY (device_type_id) REFERENCES public.devices_types(id) NOT VALID;


--
-- Name: devices devices_device_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_device_type_id_fkey FOREIGN KEY (device_type_id) REFERENCES public.devices_types(id);


--
-- Name: devices devices_user_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_user_fkey FOREIGN KEY ("user") REFERENCES public.users(login) NOT VALID;


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
-- Name: TABLE devices; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,REFERENCES,DELETE,UPDATE ON TABLE public.devices TO "www-group";


--
-- Name: TABLE sensors; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,UPDATE ON TABLE public.sensors TO "www-group";


--
-- Name: TABLE sensors_data; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,REFERENCES,DELETE,UPDATE ON TABLE public.sensors_data TO "www-group";


--
-- Name: TABLE users; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.users TO "www-group";


--
-- PostgreSQL database dump complete
--

