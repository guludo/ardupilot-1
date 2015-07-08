#!/bin/bash

src=~/ardupilot
base=$src/libraries
declare -A header_dirs

has_path(){
    local term=$1
    for p in "${@:2}"; do
        [[ "$term" == "$p" ]] && return 0
    done
    return 1
}

replace_include(){
    local file=$1
    local n=$2
    local new_path=$3
    local old_path=$4
    local regex="\(#\s*include\s*\)[<\"].\+[>\"]"
    echo "$file:$n: $old_path -->  $new_path"
    if ! sed -i "${n}s,$regex,\1$new_path," $file; then
        echo Error on executing command: sed -i "${n}s,$regex,\1$new_path," $file >&2
        kill -SIGINT $$
    fi
}

fix_includes(){
    local file=$1
    local header=$2
    local dirs=(${header_dirs[$header]})
    local num_dirs=${#dirs[@]}
    local regex="#\s*include\s*[<\"]\(.*/\)\?$header[>\"]"

    grep -ahno $regex $file | while IFS=":" read n match; do
        path=$(echo $match | sed "s/^#\s*include\s*//g")
        delim=${path:0:1}
        path=${path:1:(${#path}-2)}
        file_dir=$(realpath $(dirname $file))

        if [[ $delim == "\"" ]]; then
            localpath=$file_dir/$path
            if [[ -f $localpath ]]; then
                # verify if file is under to the file dir
                localpath=$(realpath $localpath)
                [[ $localpath == $file_dir* ]] && continue

                # if not under file dir, check if $localpath is under $base
                if [[ $localpath == $base* ]]; then
                    new_path=${localpath#$base/}
                    replace_include $file $n \<$new_path\> \"$path\"
                    continue
                fi
            fi
        fi

        match_count=0
        possible_paths=()
        for dir in "${dirs[@]}"; do
            if [[ $dir/$header == *$path ]]; then
                ((match_count++))
                new_path=$dir/$header
                possible_paths[${#possible_paths[@]}]=$new_path
            fi
        done

        if [[ $match_count -eq 0 ]]; then
            echo "$file:$n: couldn't find a match for inclusion of $path"
        elif [[ $match_count -eq 1 ]]; then
            # check if included header is under file dir
            if [[ -f $file_dir/$path ]]; then
                new_path=\"$(realpath $file_dir/$path --relative-to $file_dir)\"
            else
                new_path=\<$new_path\>
            fi
            if [[ $delim == '"' ]]; then path=\"$path\"; else path=\<$path\>; fi
            replace_include $file $n $new_path $path
        else
            echo "$file:$n: more than one match for inclusion of $path"
            echo "    possible paths:"
            for p in "${possible_paths[@]}"; do
                echo "    $p"
            done
        fi
    done
}

trap_reset_tree(){
    echo
    echo Process killed or interrupted! Reseting tree...
    git -C $src reset --hard
    exit 1
}

trap trap_reset_tree SIGINT SIGKILL

if ! git -C $src diff-files --quiet --exit-code; then
    echo You have unstaged changes, please commit or stash them beforehand >&2
    exit 1
fi

pushd $src > /dev/null

# collect all headers
git -C $base ls-files *.h > /tmp/headers
total=$(cat /tmp/headers | wc -l)
header_max_len=0
while read f; do
    header=$(basename $f)
    dir=$(dirname $f)
    if [[ -z ${header_dirs[$header]} ]]; then
        header_dirs[$header]=$dir
    else
        header_dirs[$header]+=" $dir"
    fi
    printf "\rCollecting header files paths... $((++i))/$total" >&2
    [[ ${#header} -gt $header_max_len ]] && header_max_len=${#header}
done </tmp/headers
echo

total=${#header_dirs[@]}
i=0
for header in "${!header_dirs[@]}"; do
    regex="#\s*include\s*[<\"]\(.*/\)\?$header[>\"]"
    printf "\r($((++i))/$total) Fixing includes for header %-${header_max_len}s" $header >&2

    # for each file that includes $header
    git grep -l $regex | while read f; do
        fix_includes $f $header
    done
done

popd > /dev/null
