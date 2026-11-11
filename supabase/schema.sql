-- ============================================================
--  Mémoire du podcast : à coller dans Supabase > SQL Editor > Run
-- ============================================================

-- 1) Tables --------------------------------------------------
create table if not exists articles (
  id bigserial primary key,
  source text,
  title text not null,
  summary text,
  link text unique,
  published timestamptz not null default now(),
  tsv tsvector generated always as (
    to_tsvector('french', coalesce(title, '') || ' ' || coalesce(summary, ''))
  ) stored
);

create table if not exists podcasts (
  date date primary key,
  duree_s int,
  script text
);

create table if not exists podcast_topics (
  id bigserial primary key,
  date date not null,
  nom text not null,
  domaine text,
  texte text,
  chiffres jsonb not null default '[]',
  a_retenir text,
  jury jsonb,
  termes jsonb not null default '[]',
  approfondi boolean not null default false,
  tsv tsvector generated always as (
    to_tsvector('french', coalesce(nom, '') || ' ' || coalesce(texte, '') || ' ' || coalesce(a_retenir, ''))
  ) stored
);

create table if not exists glossaire (
  terme text primary key,
  definition text,
  domaine text,
  premiere_date date
);

create table if not exists documents (
  id bigserial primary key,
  doc text not null,
  page int,
  content text not null,
  tsv tsvector generated always as (to_tsvector('french', content)) stored
);

create table if not exists utilisateurs (
  chat_id bigint primary key,
  nom text,
  cree_le timestamptz not null default now()
);

-- 2) Index de recherche --------------------------------------
create index if not exists articles_tsv_idx on articles using gin (tsv);
create index if not exists articles_pub_idx on articles (published);
create index if not exists topics_tsv_idx on podcast_topics using gin (tsv);
create index if not exists topics_date_idx on podcast_topics (date);
create index if not exists documents_tsv_idx on documents using gin (tsv);
create index if not exists documents_doc_idx on documents (doc);

-- 3) Sécurité : personne d'autre que ta clé secrète ne peut lire ces tables
alter table articles enable row level security;
alter table podcasts enable row level security;
alter table podcast_topics enable row level security;
alter table glossaire enable row level security;
alter table documents enable row level security;
alter table utilisateurs enable row level security;

-- 4) Fonctions de recherche (mots-clés, en français) ----------
create or replace function requete(q text) returns tsquery
language plpgsql stable as $$
declare s text;
begin
  select string_agg(w, ' | ') into s
  from regexp_split_to_table(
         regexp_replace(lower(q), '[^a-z0-9àâäçéèêëîïôöùûüÿœæ]+', ' ', 'g'), ' ') as w
  where length(w) > 2;
  if s is null then return null; end if;
  return to_tsquery('french', s);
end;
$$;

create or replace function chercher_docs(q text, n int default 4)
returns table (doc text, page int, content text, score real)
language sql stable as $$
  select d.doc, d.page, d.content, ts_rank(d.tsv, requete(q))
  from documents d
  where d.tsv @@ requete(q)
  order by 4 desc
  limit n;
$$;

create or replace function chercher_articles(q text, n int default 10)
returns table (source text, title text, summary text, link text, published timestamptz, score real)
language sql stable as $$
  select a.source, a.title, a.summary, a.link, a.published, ts_rank(a.tsv, requete(q))
  from articles a
  where a.tsv @@ requete(q) and a.published > now() - interval '120 days'
  order by 6 desc, a.published desc
  limit n;
$$;

create or replace function chercher_sujets(q text, n int default 6)
returns table (jour date, nom text, domaine text, texte text, a_retenir text, chiffres jsonb, score real)
language sql stable as $$
  select t.date, t.nom, t.domaine, t.texte, t.a_retenir, t.chiffres, ts_rank(t.tsv, requete(q))
  from podcast_topics t
  where t.tsv @@ requete(q)
  order by 7 desc, t.date desc
  limit n;
$$;

-- 5) Autorisations pour la clé secrète (obligatoires sur les projets récents)
grant usage on schema public to service_role;
grant select, insert, update, delete on all tables in schema public to service_role;
grant usage, select on all sequences in schema public to service_role;
grant execute on all functions in schema public to service_role;
