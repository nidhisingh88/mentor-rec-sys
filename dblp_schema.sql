CREATE TABLE Field (k text, i text, p text, v text);
COPY Field FROM '/Users/phnl310192764/dmo-other-predictive_analytics/data-science/notebooks/nidhi_aurora/PMI/fields.txt';

CREATE INDEX pub_key ON Field (k);

--remove duplicate author names present in the same publication
--for e.g. author Bo Xu occurs twice 'in Hierarchical Memory Networks for Answer Selection on Unknown Words publication'

DELETE FROM Field USING Field f2
WHERE Field.k=f2.k and Field.p='author' and Field.v=f2.v and Field.i>f2.i;

---------------CREATE Author, Pubs and Author_Of Tables in DBLP DB------------
CREATE TABLE Author (
  auth_id serial UNIQUE NOT NULL,
  auth_name text PRIMARY KEY
);

CREATE TABLE Pubs (
  pub_id serial PRIMARY KEY,
  pub_key text UNIQUE NOT NULL,
  pub_title text NOT NULL,
  pub_year text NOT NULL
);

CREATE TABLE Author_Of (
  auth_id int REFERENCES Author (auth_id) ON UPDATE CASCADE ON DELETE CASCADE,
  pub_id int REFERENCES Pubs (pub_id) ON UPDATE CASCADE ,
  CONSTRAINT Author_Of_pkey PRIMARY KEY (auth_id, pub_id)
);

CREATE TEMPORARY TABLE temp_field1(t_id serial, t_key text, t_title text , t_year text);

INSERT INTO temp_field1(SELECT nextval('temp_field1_t_id_seq') ,f1.k, f1.v, f2.v FROM Field f1, Field f2
WHERE f1.k=f2.k and f1.p='title' and f2.p='year');

CREATE INDEX t_k1 ON temp_field1 (t_key);
CREATE INDEX t_t1 ON temp_field1(t_title);
CREATE INDEX t_y1 ON temp_field1 (t_year);

DELETE FROM temp_field1 USING temp_field1 f2
WHERE temp_field1.t_key=f2.t_key and temp_field1.t_id>f2.t_id;

INSERT INTO Pubs(pub_id, pub_key, pub_title, pub_year)(
    SELECT DISTINCT * FROM temp_field1);

CREATE TEMPORARY TABLE temp_auth(t_auth_id serial, t_name text);
INSERT INTO temp_auth(SELECT nextval('temp_auth_t_auth_id_seq'), v FROM Field WHERE p='author');
DELETE FROM temp_auth USING temp_auth a2
  WHERE temp_auth.t_name = a2.t_name and temp_auth.t_auth_id>a2.t_auth_id;

INSERT INTO Author (SELECT DISTINCT * FROM temp_auth);

INSERT INTO Pubs (SELECT nextval('pubs_pub_id_seq') as pub_id, f1.k, f1.v, f2.v FROM Field f1, Field f2
WHERE f1.k=f2.k and f1.p='title' and f2.p='year');

INSERT INTO Author_Of (SELECT auth_id, pub_id FROM Author, Pubs, Field f
WHERE f.k=pub_key and f.p='author' and f.v=auth_name);


--------------------ALTER TABLES to insert and update required columns-----------
-- Create Pubs table copy and add new columns Pub language and authors count
CREATE TABLE Pubs_copy AS SELECT * FROM Pubs;
ALTER TABLE Pubs_copy ADD COLUMN pub_lang character varying(50) NOT NULL DEFAULT '';
ALTER TABLE Pubs_copy ADD COLUMN pub_auth_count INT NOT NULL DEFAULT 0;

UPDATE Pubs_copy
SET    pub_auth_count = t2.auth_count
  FROM (SELECT pub_id, COUNT(auth_id) as auth_count FROM Author_Of Group by pub_id) as t2
WHERE  Pubs_copy.pub_id = t2.pub_id;


-- For authors calculate co-authorship score and total publications
ALTER TABLE Author ADD COLUMN co_auth_score INT NOT NULL DEFAULT 0;
ALTER TABLE Author ADD COLUMN total_pubs INT NOT NULL DEFAULT 0;

CREATE TEMPORARY TABLE temp_auth1(aid int, a_name text, p_id text, p_title text, pac INT);
INSERT into temp_auth1(SELECT a.auth_id, a.auth_name, p.pub_id, p.pub_title, p.pub_auth_count FROM Author as a, Author_Of as a1, Pubs_copy as p
WHERE a.auth_id=a1.auth_id and a1.pub_id=p.pub_id);

UPDATE Author
SET co_auth_score = t2.co_auth
    FROM (SELECT aid, sum(1/pac) as co_auth from temp_auth1 GROUP BY aid) as t2
WHERE t2.aid=Author.auth_id;

UPDATE Author
SET total_pubs = t2.t_pubs
    FROM (SELECT aid, count(p_id) as t_pubs from temp_auth1 GROUP BY aid) as t2
WHERE t2.aid=Author.auth_id;

--insert from temp table into a new table and drop temp table
SELECT * INTO Author_Extra FROM temp_auth1;
DROP TABLE temp_auth1;