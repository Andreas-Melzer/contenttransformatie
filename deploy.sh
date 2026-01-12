az acr login --name registrycustoms --resource-group rg_federated-customs
docker build -f DOCKERFILE -t registrycustoms.azurecr.io/contentcreatie:latest .
docker push registrycustoms.azurecr.io/contentcreatie:latest
IMAGE_SHA=$(docker inspect --format='{{index .RepoDigests 0}}' registrycustoms.azurecr.io/contentcreatie:latest)
az containerapp update \
  --name contentcreatie \
  --resource-group ino-rg-kis-poc \
  --image $IMAGE_SHA