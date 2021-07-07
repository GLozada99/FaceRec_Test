USE DATABASE FaceRecog

CREATE TABLE pictures(
        Person_Name VARCHAR(25),
        Number INTEGER,
        Bytes LONGBLOB,
        Encoding BLOB,
        CONSTRAINT PRIMARY KEY (Person_Name, Number)
);

