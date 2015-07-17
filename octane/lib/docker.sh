confdir="/etc/dockerctl"
. ${confdir}/config
. /usr/share/dockerctl/functions

set -x

function extract_patch_files() {
	sed -nr '/\+{3}/ {s,\+{3} (b/)?([^\t]+).*,\2,g;p}'
} 

function extract_files_from_docker() {
	local container_name=$1
	shift
	shell_container ${container_name} tar cvf - $*
} 

function compare_files() {
	local container=$1
	local prefix=$2
	local file="/"$3
	local local_md5sum=`md5sum ${prefix}/${file} | cut -d" " -f1`
	local container_md5sum=`dockerctl shell ${container} md5sum ${file} | cut -d" " -f1`
	test "${local_md5sum}" = "${container_md5sum}"
	
	
} 

function put_files_to_docker() {
	local container_name=$1
	local prefix=/
	local source=$3
	local f=""
	(cd ${source} && tar cvf - *) | shell_container ${container_name} tar -xv --overwrite -f - -C ${prefix} 
	for f in `(cd ${source} && find . -type f)`; do
		compare_files ${container_name} ${source} ${f} || {
			echo "${container_name}/${f} invalid md5sum"
			exit 2
		} 
	done
	
} 

# example docker_patch cobbler / patches/hostname.patch patches/another.patch
function do_docker_patch() {
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
	prefix=`dirname $patch_files`


	extract_files_from_docker ${container} ${patch_files} | tar xvf - -C ${patch_dir}

	sed -r '/\+{3}/ {s,(.*/)([^ ]+) .*,+++ \2,g}' ${patchs} | patch ${PATCH_EXTRA_ARGS} -N -p0 -d ${patch_dir}/${prefix} && put_files_to_docker ${container} ${prefix} ${patch_dir} 

	test -d $patch_dir && rm -rf ${patch_dir} 
} 

function docker_patch() {
    local CONTAINER_NAME=$1
    local PATCH_PREFIX=$2
    shift 2
    local PATCHS=$*

    test -z "$CONTAINER_NAME" -o -z "${PATCH_PREFIX}" -o -z "${PATCHS}" && {
	    echo "Usage $0 <container_name> <patch_prefix> <patch1> <patch2>" > /dev/stderr
	    exit 2
    } 

    do_docker_patch ${CONTAINER_NAME} ${PATCH_PREFIX} $*
} 

function install_octane_nailgun() {
	local OCTANE_NAILGUN="${CWD}/../octane_nailgun"
	( 
		cd ${OCTANE_NAILGUN}
		python setup.py bdist_wheel
		cd dist	
		filename=`find . -type f -iname '*.whl' -print -quit`
		dockerctl copy ${filename} nailgun:/root/
		dockerctl shell nailgun pip install -U /root/${filename}
        dockerctl shell nailgun pkill -f wsgi
	) 
}

function install_octane_fuelclient() {
    local OCTANE_FUELCLIENT="${CWD}/../octane_fuelclient"
    pip install -U ${OCTANE_FUELCLIENT}
}

function uninstall_octane_fuelclient() {
    local OCTANE_FUELCLIENT="${CWD}/../octane_fuelclient"
    pip uninstall ${OCTANE_FUELCLIENT}
}

function patch_all_containers() {
       docker_patch astute /usr/lib64/ruby/gems/2.1.0/gems/astute-6.1.0/lib/astute ${CWD}/docker/astute/resources/deploy_actions.rb.patch
       shell_container astute supervisorctl restart astute
       docker_patch cobbler /usr/lib/python2.6/site-packages/cobbler ${CWD}/docker/cobbler/resources/pmanager.py.patch
       docker_patch nailgun /usr/lib/python2.6/site-packages/nailgun/volumes ${CWD}/docker/nailgun/resources/manager.py.patch
       docker_patch nailgun / ${CWD}/../octane_nailgun/tools/urls.py.patch
} 
