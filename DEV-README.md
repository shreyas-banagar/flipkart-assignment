TODOS:

1. Ingestion status is not getting updated with the number of rows inserted. Fix that.


COMMANDS:

Copy DB from docker container to Windows

docker cp <container_name>:<path_in_container> <path_on_windows>

docker cp flipkart-postgres:/tmp/mydatabase.backup C:\Backups\flipkart.backup

DB Backup:

docker exec <container_name> pg_dump -U <user> -d <database> -F c > C:\Backups\<database>.backup

docker exec flipkart-postgres pg_dump -U postgres -d flipkart -F c > C:\Backups\flipkart_1_0.backup

Empty DB creation:

docker exec <container_name> psql -U <user> -d <database> -c "CREATE DATABASE <database>"

docker exec flipkart-postgres psql -U postgres -c "CREATE DATABASE flipkart"

DB Restore:
docker cp C:\Backups\<backup_file>.backup <container_name>:/tmp/<database>.backup

docker cp C:\Backups\flipkart.backup flipkart-postgres:/tmp/flipkart.backup

docker exec <container_name> pg_restore -U <user> -d <database> < /tmp/<database>.backup

docker exec flipkart-postgres pg_restore -U postgres -d flipkart /tmp/mydatabase.backup

