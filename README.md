# Repo for Oracle GoldenGate Scripts

## Requirements

    sudo yum install -y python3.12 python3.12-requests python3.12-pip    

## How to use this repo
 
1. Clone the repo: 

    ```
    git clone <URL>
    ```

2. Go to the directory: 

    ```
    cd goldengate
    ```
    
3. Create Python Virtual Env:
    
    ```
    python3.12 -m venv env
    ```
    
4. Install dependencies:
    
    ```
    pip install -r requirements.txt
    ```
5. Configure Oracle Client

    ```
    export ORACLE_BASE=/u01/app/oracle
    export TNS_ADMIN=/u01/app/oracle/network/admin
    export ORACLE_HOME=${ORACLE_BASE}/product/21.3.0.0/client_1
    export PATH=${ORACLE_HOME}/bin:$PATH
    ```

9. Create secure password store (optional)
   
    ```
    mkdir wallet

    # Create wallet
    $ORACLE_HOME/bin/orapki wallet create -wallet wallet -auto_login_local

    # Add Credential
    $ORACLE_HOME/bin/mkstore -wrl wallet -createCredential <alias> <username>

    # Display credentials
    $ORACLE_HOME/bin/mkstore -wrl wallet -listCredential

    # eventuelly the sqlnet/sqlnet.ora must be changed
    ```

## Python Virtual Environment

 ```
 source env/bin/activate
 ```

## [deploy_prms.py](deploy_prms.py)

```
usage: deploy_prms.py [-h] [-f] [-p PASSWORD] config_file {prod} {create_configuration_file,replace_configuration_file}

Generates and deploys all prm files associated to the given environment

positional arguments:
  config_file           config file (json)
  {prod}                environment

optional arguments:
  -h, --help            show this help message and exit
  -f, --force           stop the processes with force
  -p PASSWORD, --password PASSWORD
                        GGADMIN password

This script performs the following tasks:

1. the extract process is stopped
2. the replicat process stopped
3. all associated prm files are uploaded using the given command
4. the extract process is started
5. the replicat process is started

Example: create all prm files for the prod environment and uploads them

    ./deploy_prms.py config.json prod

```


## [gen_prms.py](gen_prms.py)

```
usage: gen_prms.py [-h] config_file {prod}

Generates all prm files for Oracle Goldengate

positional arguments:
  config_file       config file (json)
  {prod}  environment

optional arguments:
  -h, --help        show this help message and exit
  -v, --verbose	    enable more verbose output
  --pwd_source_db   Password for source db
```


Example 1: generates the prm files for prod
  
    ./gen_prms.py config.json prod

Example 3: generates the prm files for prod with a password for the source db
  
    ./gen_prms.py config.json prod --pwd_source_db "password"

## [gen_ldz.py](gen_ldz.py)

```
usage: gen_ldz.py [-h] [-v] [--delta] [--dryrun] [--filter_step {create_tables,tables_add_ons,drop_lobs}] [--filter_table FILTER_TABLE] [--pwd_db PWD_DB] config_file {env}

Generates the SQLs to create all objects in the landingzone database

positional arguments:
  config_file           config file (json)
  {prod}                environment

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         verbose
  --delta               generates only the missing tables at the target
  --dryrun              tests the execution, does't makes any modification at the database
  --filter_step {create_tables,tables_add_ons,drop_lobs}
                        only the given step will be generated
  --filter_table FILTER_TABLE
                        only the SQLs for the given table will be generated
  --pwd_db PWD_DB       Password for source db

Example 1: generates the SQLs for the LandingZone on prod

    ./gen_ldz.py config.json prod
```

## [gg.py](gg.py)

```
usage: gg.py [-h] [--client_cert CLIENT_CERT] [--client_key CLIENT_KEY] [--command_arg COMMAND_ARG] [--command_arg_fn COMMAND_ARG_FN] [--command_args_json COMMAND_ARGS_JSON] [--gg_endpoint_url GG_ENDPOINT_URL] [--password PASSWORD]
             [--verify_cert VERIFY_CERT] [-v]
             config_file env
             {list_extracts,extract_retrieve_status,update_extract,extract_issue_command,retrieve_extract,list_replicats,replicat_retrieve_status,update_replicat,replicat_issue_command,retrieve_replicat,list_config_files,create_configuration_file,delete_configuration_file,replace_configuration_file,retrieve_configuration_file,list_configuration_data_types,list_configuration_values,execute_command,events,logs,logs_restapi,messages}

Communicates with Oracle GoldenGate Micrsoervices Architecture (GG MA) via ReST


positional arguments:
  config_file           config file (json)
  env                   environment
  {list_extracts,extract_retrieve_status,update_extract,extract_issue_command,retrieve_extract,list_replicats,replicat_retrieve_status,update_replicat,replicat_issue_command,retrieve_replicat,list_config_files,create_configuration_file,delete_configuration_file,replace_configuration_file,retrieve_configuration_file,list_configuration_data_types,list_configuration_values,execute_command,events,logs,logs_restapi,messages}
                        command

optional arguments:
  -h, --help            show this help message and exit
  --client_cert CLIENT_CERT
                        path to a client certificate file
  --client_key CLIENT_KEY
                        path to a client key file
  --command_arg COMMAND_ARG
                        single argument for the command
  --command_arg_fn COMMAND_ARG_FN
                        file name as an argument
  --command_args_json COMMAND_ARGS_JSON
                        json as an arguement
  --gg_endpoint_url GG_ENDPOINT_URL
                        overrides the url in the config
  --password PASSWORD   password for the gg api, if not given, will be asked
  --verify_cert VERIFY_CERT
                        path to a file to verify the server certificates
  -v, --verbose         increase output verbosity

Examples Commands for Extracts

    ./gg.py config.json prod list_extracts
    ./gg.py config.json prod retrieve_extract --command_arg EXT
    ./gg.py config.json prod extract_retrieve_status --command_arg EXT
    ./gg.py config.json prod update_extract --command_arg EXT --command_args_json '{"credentials": {"alias": "GGADMIN", "domain": "OracleGoldenGate"}}'
    ./gg.py config.json prod extract_issue_command --command_arg EXT --command_args_json '{"command": "STOP"}'
    ./gg.py config.json prod extract_issue_command --command_arg EXT --command_args_json '{"command": "FORCESTOP"}'

Examples Commands for Replicats

    ./gg.py config.json prod list_replicats
    ./gg.py config.json prod retrieve_replicat --command_arg REP
    ./gg.py config.json prod replicat_retrieve_status --command_arg REP
    ./gg.py config.json prod update_replicat --command_arg REP --command_args_json '{"credentials": {"alias": "GGADMIN", "domain": "OracleGoldenGate"}}'
    ./gg.py config.json prod replicat_issue_command --command_arg REP --command_args_json '{"command": "STOP"}'
    ./gg.py config.json prod replicat_issue_command --command_arg REP --command_args_json '{"command": "FORCESTOP"}'

Examples Commands for Configuration Files

    ./gg.py config.json prod list_config_files
    ./gg.py config.json prod retrieve_configuration_file --command_arg EXT.prm --command_arg_fn EXT.prm
    ./gg.py config.json prod create_configuration_file --command_arg  EXT.prm --command_arg_fn EXT.prm
    ./gg.py config.json prod delete_configuration_file --command_arg  EXT.prm --command_arg_fn EXT.prm
    ./gg.py config.json prod replace_configuration_file --command_arg  EXT.prm --command_arg EXT.prm

Examples Commands for Configuration Data Types

    ./gg.py config.json prod list_configuration_data_types

Examples Commands for Configuration Values

    ./gg.py config.json prod list_configuration_values --command_arg collectionItem
    ./gg.py config.json prod list_configuration_values --command_arg authorizationProfile
    ./gg.py config.json prod list_configuration_values --command_arg managedProcessSettings

Common Commands

    ./gg.py config.json prod execute_command --command_args_json '{"name": "start", "processName": "REP", "processType": "replicat"}'
    ./gg.py config.json prod execute_command --command_args_json '{"name": "start", "processName": "EXT", "processType": "extract"}'

```

## [config.json](config.json)
This is the central file for configuring all GG environments. 

## [monitoring_config.json](monitoring_config.json)
This is the central file for the monitoring configuration.

### default templates
A default template defines which template must be used, if there are not specific templates for the environment. 

Example
```
 "default_templates": {
    "extract": {
        "process": "extract.j2",
        "process_tables": "ext_table.j2"
    },
    "replicat": {
        "process": "replicat.j2",
        "process_tables": "rep_table.j2"
    }
 }
```

### gg_endpoints
The goldengate endpoints define the URL and username. Each environment defines which endpoint must be used

Example
```
 "gg_endpoints": {
     "test": {
         "url": "https://testsrv:9200
         "user": "ggadmin"
     },
     "prod": {
         "url": "https://prodsrv:9200",
         "user": "ggadmin"
     }
 }
```

### environments
Each enviroment contain all subsections to define the replication, for example: gg_endpoint, source_db, target_db, input_tables, extract and replicat parameters.
Optionally each environment can define its own template

Example
```
 "test": {
     "gg_endpoint": "test",
     "source_db": {
         "db_name": "SRC_DB",
         "user": "GGADMIN"
     },
     "target_db": {
         "db_name": "TGT_DB"
     },
     "tables_file": "tables.csv",
     "lobs_file": "lobs.csv",
     "trail": "/u01/app/oracle/gg_deployments/var/lib/data/es",
     "extract": {
          "process_name": "EXT",
          "credential_name": "GGADMIN_SRC_DB",
          "prm_file_name": "EXT.prm",
          "prm_table_file_name": "EXT_TABLES.prm"

     },
     "replicat": {
          "process_name": "REP",
          "credential_name": "GGADMIN_TGT_DB",
          "prm_file_name": "REP.prm",
          "prm_table_file_name": "REP_TABLES.prm"
     }
 }
```

## Templates

### [extract.j2](j2/extract.j2)
(Jinja) Template for the extract process

### [ext_table.j2](j2/extract.j2)
Single table (Jinja) template for the extract process

### [replicat.j2](j2/replicat.j2)
(Jinja) Template for the replicat process

### [rep_table.j2](j2/rep_table.j2)
Single table (Jinja) template for the replicat process
