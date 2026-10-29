PRAGMA foreign_keys=ON;

CREATE TABLE intento_examen (
	id INTEGER NOT NULL, 
	usuario_id VARCHAR(64) NOT NULL, 
	fecha DATETIME NOT NULL, 
	estado VARCHAR(16) NOT NULL, 
	puntaje_global FLOAT, 
	PRIMARY KEY (id), 
	CHECK (estado IN ('en_curso','finalizado'))
)

;


CREATE TABLE pregunta (
	id INTEGER NOT NULL, 
	destreza VARCHAR(16) NOT NULL, 
	nivel_mcer VARCHAR(2) NOT NULL, 
	contenido_estimulo TEXT NOT NULL, 
	opciones_json JSON, 
	respuesta_correcta TEXT, 
	metadatos_calibracion JSON NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (destreza IN ('lectura','escucha','escritura','oral')), 
	CHECK (nivel_mcer IN ('A1','A2','B1','B2','C1'))
)

;


CREATE TABLE respuesta_usuario (
	id INTEGER NOT NULL, 
	intento_id INTEGER NOT NULL, 
	pregunta_id INTEGER NOT NULL, 
	respuesta_dada TEXT NOT NULL, 
	calificacion_ia JSON, 
	retroalimentacion_ia TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(intento_id) REFERENCES intento_examen (id), 
	FOREIGN KEY(pregunta_id) REFERENCES pregunta (id)
)

;

CREATE INDEX ix_respuesta_usuario_intento_id ON respuesta_usuario (intento_id);
CREATE INDEX ix_respuesta_usuario_pregunta_id ON respuesta_usuario (pregunta_id);