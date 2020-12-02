# airflow_data_migration_poc

Step1: Clone the project in your system

Step2: Go to the project folder and run the below command(docker must be installed in your system)
        
	docker-compose -f docker-compose.yml up -d
        
	This will pull the relevant softwares associated with airflow.

Step3: Run the command: 

	'docker ps'    ---> this will list down all the conainers which are running. Copy the postgres container name and run the below command to get into the container bash:
      
      docker exec -it postgres_container_name bash
      
Step4: Once you are inside the container bash, run the below commands to setup the src and dest db for the tool data migration:

psql -U airflow

CREATE DATABASE src;

CREATE DATABASE dest;

\c src;

CREATE TABLE employee (
	id serial PRIMARY KEY,
	name VARCHAR ( 50 ) NOT NULL,
	email VARCHAR ( 255 ) NOT NULL
);

INSERT INTO 
    employee (name, email)
VALUES
    ('Peter','peter@email.com'),
    ('Tony','tony@email.com'),
    ('Bruce','bruce@email.com'),
    ('John','john@email.com'),
    ('Jessie','jessie@email.com'),
    ('Jackie','jackie@email.com');

 \c dest;

 CREATE TABLE employee (
	id serial PRIMARY KEY,
	name VARCHAR ( 50 ) NOT NULL,
	email VARCHAR ( 255 ) NOT NULL
);

Step5: Go to any browser and open the localhost:8080 in it.(you can see the airflow UI in it)

Step6: Turn on the dag by clicking on the toggle button and then run the dag using the play button in the UI.



For changes in the dag, you can go to the folder - dags and update the corresponding python file.





