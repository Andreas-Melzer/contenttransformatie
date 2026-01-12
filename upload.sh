az storage blob upload-batch -d containerkis/content -s content --account-name storagekis906 --overwrite --auth-mode login
az storage blob upload-batch -d containerkis/docstore -s docstore --account-name storagekis906 --overwrite --auth-mode login
az storage blob upload -c containerkis -f kme_vertaaltabel.csv -n kme_vertaaltabel.csv --account-name storagekis906 --overwrite --auth-mode login