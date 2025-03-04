
## Flask image storing service

Flask server in Docker. Gives possiblity to save pic to target volume area

Redis server in Docker is used to keep record of images (hashed filename) and given textual name

Pic added name can be queried using hash 



### Build and start

docker-compose up --build

### Add image web page usage

*http://localhost:5000/*


### Add image

*curl -X POST -F "name=Mika" -F "file=@kuva.png" http://localhost:5000/upload*

name-->filename

file-->path tobe saved file


### Check name for image hash

*curl -X GET http://localhost:5000/lookup/234dd59656f803ce7b553579dcf0054ac236032a838f462ef5425d8dc023db4f*

### Get all Redis data

curl -X GET http://localhost:5000/api/get_all_keys



### Check both container logs

*docker-compose logs -f*
