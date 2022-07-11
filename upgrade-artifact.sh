#!/bin/bash
set -euo pipefail

dante_build=$(
    az pipelines build list \
        --organization https://dev.azure.com/WTGOps \
        --project InfrastructureAutomation \
        --definition-ids 26 \
        --reason individualCI \
        --status completed \
        --result succeeded \
        --top 1 \
    | yq '.[0]'
)
dante_build_date=$(<<< "$dante_build" jq -r '.queueTime')

virgil_build=$(
    az pipelines build list \
        --organization https://dev.azure.com/WTGOps \
        --project InfrastructureAutomation \
        --definition-ids 4 \
        --reason individualCI \
        --status completed \
        --result succeeded \
        --top 1 \
    | yq '.[0]'
)
virgil_build_date=$(<<< "$virgil_build" jq -r '.queueTime')

(
    echo ---
    echo variables:
    echo "    # $(<<< "$dante_build" jq -r '.definition.name')" \
               "$(<<< "$dante_build" jq -r '.buildNumber')"
    echo "    # $(date --date="$dante_build_date" --utc) --" \
               "$(TZ=Australia/Sydney date --date="$dante_build_date")"
    echo "    #"
    echo "    # $(<<< "$dante_build" jq -r '.triggerInfo."ci.message"')"
    echo "    # $(<<< "$dante_build" jq -r '.triggerInfo."ci.sourceSha"')"
    echo "    dante_build_id: '$(<<< "$dante_build" jq -r '.id')'"
    echo
    echo "    # $(<<< "$virgil_build" jq -r '.definition.name')" \
               "$(<<< "$virgil_build" jq -r '.buildNumber')"
    echo "    # $(date --date="$virgil_build_date" --utc) --" \
               "$(TZ=Australia/Sydney date --date="$virgil_build_date")"
    echo "    #"
    echo "    # $(<<< "$virgil_build" jq -r '.triggerInfo."ci.message"')"
    echo "    # $(<<< "$virgil_build" jq -r '.triggerInfo."ci.sourceSha"')"
    echo "    virgil_build_id: '$(<<< "$virgil_build" jq -r '.id')'"
) | tee artifacts.yml
