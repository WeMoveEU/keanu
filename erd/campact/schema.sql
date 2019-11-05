

CREATE TABLE public.donation_created (
    id character varying(32) NOT NULL,
    event_timestamp timestamp with time zone NOT NULL,
    event_count integer DEFAULT 1 NOT NULL,
    aggregation_interval integer NOT NULL,
    utm_medium text,
    utm_source text,
    utm_campaign text,
    utm_content text,
    utm_term text,
    source_system text NOT NULL,
    source_path text NOT NULL,
    amount integer NOT NULL,
    promotional_code character varying NOT NULL,
    payment_type public.payment_type
);



CREATE TABLE public.mail_opened (
    id character varying(32) NOT NULL,
    event_timestamp timestamp with time zone NOT NULL,
    event_count integer DEFAULT 1 NOT NULL,
    aggregation_interval integer,
    utm_medium text,
    utm_source text,
    utm_campaign text,
    utm_content text,
    utm_term text
);




CREATE TABLE public.mail_sent (
    id character varying(32) NOT NULL,
    event_timestamp timestamp with time zone NOT NULL,
    event_count integer DEFAULT 1 NOT NULL,
    aggregation_interval integer,
    utm_medium text,
    utm_source text,
    utm_campaign text,
    utm_content text,
    utm_term text
);




CREATE TABLE public.mail_visited (
    id character varying(32) NOT NULL,
    event_timestamp timestamp with time zone NOT NULL,
    event_count integer DEFAULT 1 NOT NULL,
    aggregation_interval integer,
    utm_medium text,
    utm_source text,
    utm_campaign text,
    utm_content text,
    utm_term text
);





CREATE TABLE public.signature_created (
    id character varying(32) NOT NULL,
    event_timestamp timestamp with time zone NOT NULL,
    event_count integer DEFAULT 1 NOT NULL,
    aggregation_interval integer NOT NULL,
    utm_medium text,
    utm_source text,
    utm_campaign text,
    utm_content text,
    utm_term text,
    source_system text NOT NULL,
    source_path text NOT NULL,
    nl_offer_response public.nl_offer_response
);




CREATE TABLE public.sponsorship_created (
    id character varying(32) NOT NULL,
    event_timestamp timestamp with time zone NOT NULL,
    event_count integer DEFAULT 1 NOT NULL,
    aggregation_interval integer NOT NULL,
    utm_medium text,
    utm_source text,
    utm_campaign text,
    utm_content text,
    utm_term text,
    source_system text NOT NULL,
    source_path text NOT NULL,
    amount integer NOT NULL,
    payment_type public.payment_type,
    payment_interval public.payment_interval
);





CREATE TABLE public.weact_signature_created (
    id character varying(32) NOT NULL,
    event_timestamp timestamp with time zone NOT NULL,
    event_count integer DEFAULT 1 NOT NULL,
    aggregation_interval integer NOT NULL,
    utm_medium text,
    utm_source text,
    utm_campaign text,
    utm_content text,
    utm_term text,
    source_system text NOT NULL,
    source_path text NOT NULL,
    nl_offer_response public.nl_offer_response
);

