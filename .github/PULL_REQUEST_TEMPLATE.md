## WHAT
<!-- (Write the change being made with this pull request) -->

## WHY
<!-- (Write the motivation why you submit this pull request) -->

## Self checks (Needed if you modify data sync configs under `config/`)

- [ ] You've confirmed that your data doesn't contain ’Top Secret' information

    - You can check which data is 'Top Secret' [here](https://docs.google.com/spreadsheets/d/1FQi7aQ5uknyXL1xyA9SEMneLkVYXbvY0geEXFbjpqew/edit#gid=1109800730)

- [ ] You've created a JIRA Ticket for requesting DataPlatform Team  

    - If not yet, please see:
      - [how-to-use-batchpipeline#request-to-dataplatform-team](https://microservices.mercari.in/guides/dataplatform/how-to-use-batchpipeline/#request-to-dataplatform-team)
      - [how-to-use-streampipeline#ask-dataplatform-team-to-deliver-the-logs-to-bigquery](https://microservices.mercari.in/guides/dataplatform/how-to-use-streampipeline/#ask-dataplatform-team-to-deliver-the-logs-to-bigquery)

- [ ] The changes in this PR will be applied to **development environment immediately after the PR is merged**. And will be applied to **production on the next Tuesday or Thursday**. Please contact us @ [#mp-dataplatform](https://mercari.slack.com/archives/CA0CHM5V4) if you want release it in a hurry.

## Self validations

- [ ] For [incremental update settings](https://microservices.mercari.in/guides/dataplatform/how-to-use-batchpipeline/#incremental-update-settings), you must "add new columns" only at the end of the SELECT statement column.