#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

fail() {
    printf 'Error: %s\n' "$1" >&2
    exit 1
}

dockerfile=Dockerfile
if [[ ${1:-} == --published-image ]]; then
    dockerfile=starter/Dockerfile.published
    shift
fi

case ${1:-} in
    -h|--help)
        printf 'Usage: %s [--published-image] ["Project Name" "/path/to/new-directory"]\n' "$0"
        exit 0
        ;;
esac

case $# in
    0) read -r -p 'Project name: ' project_name || fail 'Enter a project name.' ;;
    2) project_name=$1 ;;
    *) fail 'Pass both the project name and path, or run without arguments for prompts.' ;;
esac

[[ $project_name =~ ^[a-zA-Z0-9][a-zA-Z0-9_\ -]{0,17}$ && $project_name != *' ' ]] ||
    fail 'Use 1 to 18 letters, numbers, spaces, hyphens, or underscores. Start with a letter or number and omit trailing spaces.'

slug=$(printf '%s' "$project_name" | tr '[:upper:] ' '[:lower:]-')
rom_title=$(printf '%s' "$project_name" | tr '[:lower:]' '[:upper:]' | tr -cd 'A-Z0-9' | cut -c1-11)
starter_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)

if (( $# == 0 )); then
    default_path="$(dirname -- "$starter_root")/$slug"
    read -r -p "New dev directory [$default_path]: " project_path ||
        fail 'Enter a path or press Enter to accept the default.'
    project_path=${project_path:-$default_path}
else
    project_path=$2
fi

[[ -n $project_path ]] || fail 'The dev directory path is empty.'
if [[ $project_path == '~/'* ]]; then
    project_path="$HOME/${project_path:2}"
fi
[[ ! -e $project_path && ! -L $project_path ]] ||
    fail "Choose a new directory. This path already exists: $project_path"

[[ $(id -u) != 0 ]] || fail 'Run the script as your normal user with Docker access.'
docker compose version >/dev/null || fail 'Install Docker and the Docker Compose plugin.'
docker info --format '{{.ServerVersion}}' >/dev/null ||
    fail 'Start Docker and make sure your user can access it.'

mkdir -p -- "$(dirname -- "$project_path")"
mkdir -- "$project_path"
cd -- "$project_path"
project_path=$(pwd -P)
path_hash=$(printf '%s' "$project_path" | sha256sum | cut -c1-12)
compose_name="gbdk-$slug-$path_hash"

mkdir src .devcontainer .vscode
cp -- "$starter_root/$dockerfile" Dockerfile
cp -- "$starter_root"/{.dockerignore,.gitignore} .
cp -- "$starter_root/.vscode/tasks.json" .vscode/
cp -- "$starter_root/starter/devcontainer.json" .devcontainer/
sed "s/@PROJECT_NAME@/$project_name/g" "$starter_root/starter/main.c.in" > src/main.c
sed "s/@PROJECT_NAME@/$project_name/g" "$starter_root/starter/README.md.in" > README.md
sed "s/@ROM_TITLE@/$rom_title/g" "$starter_root/starter/Makefile.in" > Makefile
sed -e "s/@CONTAINER_PROJECT@/$compose_name/g" \
    -e "s/@DEV_UID@/$(id -u)/g" -e "s/@DEV_GID@/$(id -g)/g" \
    "$starter_root/starter/compose.yaml.in" > compose.yaml

compose() {
    docker compose --project-name "$compose_name" "$@"
}

cleanup() {
    if (( $? != 0 )); then
        compose down >&2 || true
        printf 'The scaffold is still at %s\n' "$project_path" >&2
    fi
}
trap cleanup EXIT

compose up -d --build >&2
compose exec -T dev git init --initial-branch=main >&2
compose exec -T dev make >&2

rom=build/game.gbc
[[ -s $rom ]] || fail 'The build did not produce a ROM.'
header_title=$(dd if="$rom" bs=1 skip=308 count="${#rom_title}" 2>/dev/null)
color_flag=$(od -An -tu1 -j323 -N1 "$rom" | tr -d '[:space:]')
[[ $header_title == "$rom_title" && $color_flag == 192 ]] ||
    fail 'The ROM header did not match the project title and Game Boy Color target.'
grep -aFq -- "$project_name" "$rom" ||
    fail 'The display title was missing from the ROM.'

printf '\nFirst ROM verified for %s\n' "$project_name"
printf 'Dev directory  %s\n' "$project_path"
printf 'ROM            %s/%s\n' "$project_path" "$rom"
printf 'Compose project %s\n' "$compose_name"
printf '\nOpen the dev directory in remote VS Code and select Dev Containers: Reopen in Container.\n'
