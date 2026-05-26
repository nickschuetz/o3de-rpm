#!/usr/bin/env bash
# Mirror COPR project metadata (description / instructions / homepage / contact)
# between hellaenergy/<project> on copr.fedorainfracloud.org and the in-repo
# copr-metadata/<project>/ directory.
#
# Usage:
#   scripts/copr-metadata.sh pull [project ...]    # COPR -> repo (overwrites local)
#   scripts/copr-metadata.sh diff [project ...]    # compare repo vs live
#   scripts/copr-metadata.sh push [project ...]    # repo -> COPR (requires copr-cli auth)
#
# With no project argument, all five are processed:
#   o3de  o3de-stabilization  o3de-development  o3de-experimental  o3de-dependencies
# (o3de-snapshot was renamed to o3de-development on 2026-05-23; the old
# project still exists on COPR but is deprecated, its source directory
# in this repo has been removed, and `make copr-metadata-push` no longer
# targets it.)
#
# The four mirrored fields per project are:
#   description.md  instructions.md  homepage.txt  contact.txt

set -euo pipefail

OWNER="hellaenergy"
ALL_PROJECTS=(o3de o3de-stabilization o3de-development o3de-experimental o3de-dependencies)
FIELDS=(description instructions homepage contact)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
META_ROOT="${REPO_ROOT}/copr-metadata"

field_filename() {
    local field=$1
    case "$field" in
        description|instructions) echo "${field}.md" ;;
        homepage|contact)         echo "${field}.txt" ;;
        *) echo "unknown field: $field" >&2; exit 2 ;;
    esac
}

fetch_live() {
    # Prints the live JSON for one project to stdout.
    local project=$1
    curl -fsS "https://copr.fedorainfracloud.org/api_3/project?ownername=${OWNER}&projectname=${project}"
}

extract_field() {
    # Read JSON on stdin, print the named field's string value.
    local field=$1
    python3 -c "
import sys, json
d = json.load(sys.stdin)
v = d.get('$field') or ''
sys.stdout.write(v)
"
}

read_local() {
    # Print the on-disk content for a project field, or empty string if missing.
    local project=$1 field=$2
    local path="${META_ROOT}/${project}/$(field_filename "$field")"
    [[ -f "$path" ]] && cat "$path" || true
}

write_local() {
    # Write content (read from stdin) to the project field's file. Ensures a
    # trailing newline if the content is non-empty and didn't already end in one.
    local project=$1 field=$2
    local dir="${META_ROOT}/${project}"
    local path="${dir}/$(field_filename "$field")"
    mkdir -p "$dir"
    local content
    content=$(cat)
    printf '%s' "$content" > "$path"
    if [[ -n "$content" && "${content: -1}" != $'\n' ]]; then
        printf '\n' >> "$path"
    fi
}

cmd_pull() {
    local projects=("$@")
    for project in "${projects[@]}"; do
        echo "Pulling ${OWNER}/${project}..."
        local json
        json=$(fetch_live "$project")
        for field in "${FIELDS[@]}"; do
            printf '%s' "$json" | extract_field "$field" | write_local "$project" "$field"
        done
        echo "  -> ${META_ROOT}/${project}/"
    done
}

cmd_diff() {
    local projects=("$@")
    local rc=0
    for project in "${projects[@]}"; do
        local json
        json=$(fetch_live "$project")
        for field in "${FIELDS[@]}"; do
            local live local_content label_live label_repo
            live=$(printf '%s' "$json" | extract_field "$field")
            # Local files end with a trailing newline (POSIX convention) but the
            # COPR side stores values without one. Compare semantic content by
            # stripping the trailing newline from local before diffing — same
            # transformation cmd_push applies before the wire call.
            local_content=$(read_local "$project" "$field")
            local_content=${local_content%$'\n'}
            label_live="live:${OWNER}/${project}/${field}"
            label_repo="repo:copr-metadata/${project}/$(field_filename "$field")"
            if ! diff -u --label "$label_live" --label "$label_repo" \
                 <(printf '%s' "$live") <(printf '%s' "$local_content") >/dev/null 2>&1; then
                echo "DRIFT: ${OWNER}/${project} ${field}"
                diff -u --label "$label_live" --label "$label_repo" \
                     <(printf '%s' "$live") <(printf '%s' "$local_content") || true
                rc=1
            fi
        done
    done
    if [[ $rc -eq 0 ]]; then
        echo "OK: live COPR metadata matches repo for: ${projects[*]}"
    fi
    return $rc
}

copr_api_creds() {
    # Echo "login token" pulled from ~/.config/copr (one shared file).
    python3 -c "
import configparser, os, sys
cfg = configparser.ConfigParser()
cfg.read(os.path.expanduser('~/.config/copr'))
sec = 'copr-cli' if cfg.has_section('copr-cli') else cfg.sections()[0]
print(cfg[sec]['login'], cfg[sec]['token'])
"
}

cmd_push() {
    local projects=("$@")
    local login token
    read -r login token < <(copr_api_creds)
    for project in "${projects[@]}"; do
        echo "Pushing repo -> ${OWNER}/${project}..."
        local description instructions homepage contact
        description=$(read_local "$project" description)
        instructions=$(read_local "$project" instructions)
        homepage=$(read_local "$project" homepage)
        contact=$(read_local "$project" contact)
        # description + instructions go via copr-cli (its supported flags).
        # Strip the trailing newline our writer adds; preserve internal blanks.
        copr-cli modify "${OWNER}/${project}" \
            --description "${description%$'\n'}" \
            --instructions "${instructions%$'\n'}"
        # homepage + contact aren't exposed as copr-cli flags — go through the
        # raw API. Empty strings would clear the field; skip if not set locally.
        local form=()
        [[ -n "${homepage%$'\n'}" ]] && form+=(-F "homepage=${homepage%$'\n'}")
        [[ -n "${contact%$'\n'}"  ]] && form+=(-F "contact=${contact%$'\n'}")
        if (( ${#form[@]} )); then
            curl -fsS -u "${login}:${token}" -X POST \
                "https://copr.fedorainfracloud.org/api_3/project/edit/${OWNER}/${project}" \
                "${form[@]}" >/dev/null
        fi
    done
}

main() {
    local action=${1:-}
    shift || true
    local projects=("$@")
    if [[ ${#projects[@]} -eq 0 ]]; then
        projects=("${ALL_PROJECTS[@]}")
    fi
    case "$action" in
        pull) cmd_pull "${projects[@]}" ;;
        diff) cmd_diff "${projects[@]}" ;;
        push) cmd_push "${projects[@]}" ;;
        *)
            echo "Usage: $0 {pull|diff|push} [project ...]" >&2
            echo "Projects: ${ALL_PROJECTS[*]}" >&2
            exit 2
            ;;
    esac
}

main "$@"
