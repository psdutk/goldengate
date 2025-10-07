-- Logminer Job  mit User ggadmin anlegen
begin
dbms_scheduler.create_job (
job_name => 'GG_LOGMINER_BUILD_JOB_PDB',
job_type => 'PLSQL_BLOCK',
job_action => 'begin
                DBMS_LOGMNR_D.BUILD( options => DBMS_LOGMNR_D.STORE_IN_REDO_LOGS);
              end;',
start_date => SYSTIMESTAMP,
repeat_interval => 'FREQ=DAILY; BYHOUR=5; BYMINUTE=1',
end_date => NULL,
enabled => TRUE,
comments => 'Täglicher Job für Logminer Build auf PDB Ebene');
END;
/

-- Logminer Job löschen
begin
dbms_scheduler.drop_job (
job_name => 'GG_LOGMINER_BUILD_JOB_PDB',
defer    => TRUE);
end;
/

-- Letze REGISTER SCN abfragen
show con_id;

SELECT DATE_OF_BUILD, START_SCN
FROM dba_logmnr_dictionary_buildlog
WHERE CONTAINER_ID = <Con_Id>
ORDER BY START_SCN DESC
FETCH FIRST 1 ROWS ONLY;

