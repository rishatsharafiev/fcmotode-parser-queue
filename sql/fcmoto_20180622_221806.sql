--
-- PostgreSQL database dump
--

-- Dumped from database version 9.6.9
-- Dumped by pg_dump version 10.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
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
-- Name: category_id_seq; Type: SEQUENCE; Schema: public; Owner: fcmoto
--

CREATE SEQUENCE public.category_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.category_id_seq OWNER TO fcmoto;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: category; Type: TABLE; Schema: public; Owner: fcmoto
--

CREATE TABLE public.category (
    id integer DEFAULT nextval('public.category_id_seq'::regclass) NOT NULL,
    url character varying(2044) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone,
    is_done boolean DEFAULT false NOT NULL,
    retry smallint DEFAULT 0 NOT NULL,
    title character varying(2044) DEFAULT ''::character varying NOT NULL,
    priority smallint DEFAULT 0 NOT NULL,
    last_page integer DEFAULT 1 NOT NULL
);


ALTER TABLE public.category OWNER TO fcmoto;

--
-- Name: page_id_seq; Type: SEQUENCE; Schema: public; Owner: fcmoto
--

CREATE SEQUENCE public.page_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.page_id_seq OWNER TO fcmoto;

--
-- Name: page; Type: TABLE; Schema: public; Owner: fcmoto
--

CREATE TABLE public.page (
    id integer DEFAULT nextval('public.page_id_seq'::regclass) NOT NULL,
    url character varying(2044) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone,
    is_done boolean DEFAULT false NOT NULL,
    category_id integer NOT NULL,
    retry smallint DEFAULT 0 NOT NULL
);


ALTER TABLE public.page OWNER TO fcmoto;

--
-- Name: product; Type: TABLE; Schema: public; Owner: fcmoto
--

CREATE TABLE public.product (
    id integer NOT NULL,
    page_id integer NOT NULL,
    url character varying(2044) NOT NULL,
    name_url character varying(2044) NOT NULL,
    back_picture character varying(2044) NOT NULL,
    colors character varying(2044) NOT NULL,
    description_html text NOT NULL,
    description_text text NOT NULL,
    front_picture character varying(2044) NOT NULL,
    manufacturer character varying(2044) NOT NULL,
    name character varying(2044) NOT NULL,
    price_cleaned character varying(2044) NOT NULL,
    is_done boolean DEFAULT false NOT NULL,
    retry smallint DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone
);


ALTER TABLE public.product OWNER TO fcmoto;

--
-- Name: product_id_seq; Type: SEQUENCE; Schema: public; Owner: fcmoto
--

CREATE SEQUENCE public.product_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.product_id_seq OWNER TO fcmoto;

--
-- Name: product_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: fcmoto
--

ALTER SEQUENCE public.product_id_seq OWNED BY public.product.id;


--
-- Name: size; Type: TABLE; Schema: public; Owner: fcmoto
--

CREATE TABLE public.size (
    id integer NOT NULL,
    product_id integer NOT NULL,
    available boolean DEFAULT false NOT NULL,
    value character varying(2044) NOT NULL
);


ALTER TABLE public.size OWNER TO fcmoto;

--
-- Name: size_id_seq; Type: SEQUENCE; Schema: public; Owner: fcmoto
--

CREATE SEQUENCE public.size_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.size_id_seq OWNER TO fcmoto;

--
-- Name: size_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: fcmoto
--

ALTER SEQUENCE public.size_id_seq OWNED BY public.size.id;


--
-- Name: product id; Type: DEFAULT; Schema: public; Owner: fcmoto
--

ALTER TABLE ONLY public.product ALTER COLUMN id SET DEFAULT nextval('public.product_id_seq'::regclass);


--
-- Name: size id; Type: DEFAULT; Schema: public; Owner: fcmoto
--

ALTER TABLE ONLY public.size ALTER COLUMN id SET DEFAULT nextval('public.size_id_seq'::regclass);


--
-- Name: category category_pkey; Type: CONSTRAINT; Schema: public; Owner: fcmoto
--

ALTER TABLE ONLY public.category
    ADD CONSTRAINT category_pkey PRIMARY KEY (id);


--
-- Name: page page_pkey; Type: CONSTRAINT; Schema: public; Owner: fcmoto
--

ALTER TABLE ONLY public.page
    ADD CONSTRAINT page_pkey PRIMARY KEY (id);


--
-- Name: product product_pkey; Type: CONSTRAINT; Schema: public; Owner: fcmoto
--

ALTER TABLE ONLY public.product
    ADD CONSTRAINT product_pkey PRIMARY KEY (id);


--
-- Name: category unique_category_id; Type: CONSTRAINT; Schema: public; Owner: fcmoto
--

ALTER TABLE ONLY public.category
    ADD CONSTRAINT unique_category_id UNIQUE (id);


--
-- Name: size unique_size_id; Type: CONSTRAINT; Schema: public; Owner: fcmoto
--

ALTER TABLE ONLY public.size
    ADD CONSTRAINT unique_size_id PRIMARY KEY (id);


--
-- Name: page unique_url_category_id; Type: CONSTRAINT; Schema: public; Owner: fcmoto
--

ALTER TABLE ONLY public.page
    ADD CONSTRAINT unique_url_category_id UNIQUE (url, category_id);


--
-- Name: product unique_url_page_id; Type: CONSTRAINT; Schema: public; Owner: fcmoto
--

ALTER TABLE ONLY public.product
    ADD CONSTRAINT unique_url_page_id UNIQUE (url, page_id);


--
-- Name: size unique_value_product_id; Type: CONSTRAINT; Schema: public; Owner: fcmoto
--

ALTER TABLE ONLY public.size
    ADD CONSTRAINT unique_value_product_id UNIQUE (value, product_id);


--
-- Name: page lnk_category_page; Type: FK CONSTRAINT; Schema: public; Owner: fcmoto
--

ALTER TABLE ONLY public.page
    ADD CONSTRAINT lnk_category_page FOREIGN KEY (category_id) REFERENCES public.category(id) MATCH FULL ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: product lnk_page_product; Type: FK CONSTRAINT; Schema: public; Owner: fcmoto
--

ALTER TABLE ONLY public.product
    ADD CONSTRAINT lnk_page_product FOREIGN KEY (page_id) REFERENCES public.page(id) MATCH FULL ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: size lnk_product_size; Type: FK CONSTRAINT; Schema: public; Owner: fcmoto
--

ALTER TABLE ONLY public.size
    ADD CONSTRAINT lnk_product_size FOREIGN KEY (product_id) REFERENCES public.product(id) MATCH FULL ON UPDATE CASCADE ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

