confdir="/etc/dockerctl"
. ${confdir}/config
. /usr/share/dockerctl/functions

#alias extract_patch_files="sed -nr '/\+{3}/ {s,\+{3} (b/)?([^\t]+).*,\2,g;p}'"

function extract_files_from_docker() {
	local container_name=$1
	shift
	shell_container ${container_name} tar cvf - $*
} 

function put_files_to_docker() {
	local container_name=$1
	local prefix=$2
	local source=$3
	(cd ${source} && tar cvf - * ) | shell_container ${container_name} tar -xv --overwrite -f - -C ${prefix} 
} 

function extract_patch_files() {
	sed -nr '/\+{3}/ {s,\+{3} (b/)?([^\t]+).*,\2,g;p}'
} 


# example docker_patch cobbler / patches/hostname.patch patches/another.patch
function docker_patch() {
	local container=$1
	local prefix=$2
	shift 2
	local patchs=$*

	list_containers | egrep -q "^${container}$" || {
		echo "Container $container not found" > /dev/stderr
		return
	} 

	for p in $patchs; do
		test -f $p || {
			echo "Patch $p not found" > /dev/stderr
			return
		} 
	done


	patch_dir=$(mktemp -d /tmp/docker_patch.XXXXXXX)

	patch_files=`cat $patchs | extract_patch_files | sed -r "/^[^\/]/ { s ^ ${prefix}/ g }"`


	extract_files_from_docker ${container} ${patch_files} | tar xvf - -C ${patch_dir}

	cat ${patchs} | patch -p0 -d ${patch_dir} && put_files_to_docker ${container} ${prefix} ${patch_dir} 

	test -d $patch_dir && rm -rf ${patch_dir} 
} 
#set -x

CONTAINER_NAME=$1
PATCH_PREFIX=$2
shift 2
PATCHS=$*

test -z "$CONTAINER_NAME" -o -z "${PATCH_PREFIX}" -o -z "${PATCHS} " && {
	echo "Usage $0 <container_name> <patch_prefix> <patch1> ...." > /dev/stderr
	exit 2
} 

docker_patch $CONTAINER_NAME $PATCH_PREFIX $*

