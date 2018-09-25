dryRun=true
numberFilesToKeep=3
curDir=$( dirname "$0")
logFile=$curDir/deleteHistory.log

jfrog rt search --spec=$curDir/jfrogfilespec.json --sort-by created | grep "\"path\":" | awk -F":" '{ print $2}' > $curDir/allRes.txt 2>/dev/null
if [ $? -ne 0 ]; then
        echo "Error in retriving all files.."
        exit 2
fi

#Read last 3 the lines from file
IFS=$'\n' read -d '' -r -a allRes < $curDir/allRes.txt
echo "${allRes[@]}"

jfrog rt search --spec=./jfrogfilespec.json --sort-by created --sort-order=asc --limit $numberFilesToKeep | grep "\"path\":" | awk -F":" '{ print $2}' > $curDir/first3Res.txt 2>/dev/null
if [ $? -ne 0 ]; then
        echo "Error in retriving 3 files.." 1>>$logFile
        exit 1
fi

echo "Lenght :: ${#allRes[@]}"
if [ ${#allRes[@]} -eq 3 ];then
        echo "NOTHING TO DO"
        #exit 3
fi

#Read last 3 the lines from file
IFS=$'\n' read -d '' -r -a first3Res < $curDir/first3Res.txt
echo "first3Res :: ${first3Res[@]}" 1>>$logFile

deleteArray=()
count=0
for path_a in "${allRes[@]}"
do
  match=false
  for path_b in "${first3Res[@]}"
  do
    if [ $path_a == $path_b ]
    then
        echo "$path_a == $path_b"
        match=true
    fi
  done
  if [ $match == false ]; then
    deleteArray[$count]=$path_a
    let "count=count+1"
  fi
done

echo "Delete Array :: ${deleteArray[@]}"

for delPath in "${deleteArray[@]}"
do
  if [ "$dryRun" == false ];then
     #jfrog rt del "$(echo $delPath)" --quiet 1>>$logFile
     jfrog rt del "$(echo $delPath | tr -d ' "')" --quiet 1>>$logFile 2>&1
  else
     jfrog rt del "$(echo $delPath | tr -d ' "')" --quiet --dry-run 1>>$logFile 2>&1
  fi
done
#jfrog rt del $del_path --quiet
#jfrog rt del exp-repo
