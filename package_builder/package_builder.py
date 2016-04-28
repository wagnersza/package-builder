#! /usr/bin/env python
# -*- coding: utf-8 -*-

import docker as docker_client
import os
import argparse
import subprocess
from   subprocess import Popen, PIPE
import sys
import dockerpty
import platform
from   io import BytesIO
import tarfile
import StringIO

def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))

def file_lines(docker_image):
    lines = [        
        "FROM %s\n" % (docker_image),
        'RUN yum install rpmdevtools wget -y\n',
        'RUN yum groupinstall "Development Tools" -y\n',
        'RUN rpmdev-setuptree\n',
    ]    
    return lines

def get_spec_file_name():
    ls = os.listdir("./rpmbuild/SPECS")
    spec_file_name = filter(lambda x:'spec' in x, ls)
    #print spec_file_name
    if len(spec_file_name) == 0:
        raise ValueError("No spec file was found on: %s" % os.getcwd())
    return "rpmbuild/SPECS/%s" % spec_file_name[0]

def make_build_require_list():
    spec_file = get_spec_file_name()
    with open(spec_file, "r") as spec:
        spec_lines = spec.readlines()
    build_requires = filter(lambda x:'BuildRequires' in x, spec_lines)
    build_require_list = []
    for i in build_requires:
        build_file = i.split()[1]
        build_require_list.append(build_file)
    return build_require_list

def make_source_list():
    spec_file = get_spec_file_name()
    with open(spec_file, "r") as spec:
        spec_lines = spec.readlines()
    sources = filter(lambda x:'Source' in x, spec_lines)
    source_list = []
    for i in sources:
        source_file = i.split()[1]
        source_list.append(source_file)
    return source_list

def append_build_require_to_docker_file(dockerfile):
    for i in make_build_require_list():
        file_line = "RUN yum install -y %s\n" % (i,)
        dockerfile.append(file_line)
    return dockerfile

def get_docker_host():
    shellinit = os.popen("docker-machine url package-builder").read()
    return shellinit.strip()

def install_docker():
    if platform.system() == 'Darwin':
        print '\n - instaling docker-machine ...\n'
        if os.system("brew cask list dockertoolbox") != 0:
            os.system("brew update") # It had raised an ruby error so I had to update brew first
            os.system("brew install Caskroom/cask/dockertoolbox") 
    else:
        print "system not suported yet"

def start_docker():
    print '\n - starting docker-machine...\n'
    os.system("docker-machine start package-builder")

def create_machine_docker():
    print '\n - creating a new vm called package-builder on docker-machine...\n'
    os.system("docker-machine create --driver virtualbox package-builder")
    
def remove_existing_docker_images(client):
    print '\n - removing existing docker images with package-builder:base_build... \n'
    if len(client.images("package-builder:base_build")) != 0:
        client.remove_image("package-builder:base_build", force=True)
    else:
        print '\n - no docker images with name package-builder:base_build found to remove... \n'    

def remove_existing_docker_containers(client):
    print '\n - removing existing docker containers with package-builder name... \n'
    containers_to_remove = client.containers(all=True, filters={'Names': 'package-builder'})
    if len(containers_to_remove) != 0:
        client.remove_container(containers_to_remove[0]['Id'],force=True)
    else:
        print '\n - no containers with name package-builder found to remove... \n'

def create_docker_container(client):
    print '\n - creating a new docker container as package-builder... \n'
    container = client.create_container(
        name='package-builder',
        image='package-builder:base_build',
        stdin_open=True,
        tty=True,
        detach=False,
        command='/bin/bash'
    )
    return container

def create_docker_image(client,file):
    print '\n - creating a new docker image as package-builder:base_build based on this Dockerfiler: \n'
    response = [line for line in client.build(
        fileobj=file,
        rm=True,
        tag='package-builder:base_build')
    ]
    return response

def transfer_tar_to_container(client,container,filedata,path):
    print '\n - transfering the tarfile to the container ... \n'
    client.put_archive(container=str(container['Id']), path=path, data=filedata )

def create_rpmbuild_tar(client, container):
    print '\n - creating a tarfile of rpmbuild folder to transfer it to the container... \n'
    make_tarfile("rpmbuild.tar", "rpmbuild")
    f = open('rpmbuild.tar', 'rb')
    return f.read()

def create_rpms_tar(client, container):
    print '\n - creating a tarfile of rpm files to transfer it to the container... \n'
    make_tarfile("rpms.tar", "rpmbuild/RPMS")
    f = open('rpms.tar', 'rb')
    return f.read()

def remove_rpmbuild_tar(tarfile):
    print '\n - removing tarfile... \n'
    os.remove(tarfile)

def build_rpm(client,container):
    print '\n - building the rpm... \n'
    container_exec = client.exec_create(container=str(container['Id']), cmd='/bin/bash -c "/usr/bin/rpmbuild -ba /root/%s"' % get_spec_file_name(), stdout=True, stderr=True, tty=True)
    return container_exec

def get_rpm_from_container(client,container):
    print '\n - getting srpm and rpm from the container... \n'
    stream, stats = client.get_archive(container=str(container['Id']), path='/root/rpmbuild')
    file_content = StringIO.StringIO(stream.read())
    tf = tarfile.open(fileobj=file_content)
    return tf

def check_dockermachine_exists_and_running():
    # Verifies that docker-machine is installed
    cmd = ['/usr/local/bin/docker-machine']
    FNULL = open(os.devnull, 'w')
    returncode = subprocess.Popen(cmd,stdout=FNULL).wait()
    if returncode != 0:
        install_docker()
    returncode = subprocess.Popen(cmd,stdout=FNULL).wait()
    if returncode != 0:
        print "Could not find or install docker machine. Please verify if the docker-machine installation was succeded "
        sys.exit(1)
    print "Everything is all right" 

    # Verifies that the vm docker called package-builder exists
    cmd = ['/usr/local/bin/docker-machine', 'status', 'package-builder'] 
    returncode = subprocess.Popen(cmd,stdout=FNULL).wait()
    if returncode != 0:
        create_machine_docker()

    # Verifies that the vm docker is running
    stdout,stderr = subprocess.Popen(cmd,stdout=PIPE).communicate()

    if stdout.strip() != 'Running':
        start_docker()
    else:
        print '\n - docker-machine package-builder is already running... \n'

def main():
    parser = argparse.ArgumentParser(prog='package-builder', description='Make loca enviroment to build OS packages with docker')
    parser.add_argument("-u", "--up", action="store_true", help="install and start local enviroment")
    parser.add_argument("-b", "--build", action="store_true", help="build OS package")
    parser.add_argument("-t", "--test", action="store_true", help="start shell with a clean container and copy package to test it") 
    parser.add_argument("-i", "--image", default='centos:centos7', help="docker image, default: centos:centos7, see the options in https://registry.hub.docker.com") 
    parser.add_argument("-d", "--debug", action="store_true", help='print more logs') 

    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    # docker
    docker = docker_client.Client(base_url=get_docker_host(),timeout=3000)

    # Start: package-builder --up
    if args.up == True:
        check_dockermachine_exists_and_running()
    
    # Build: packege-builder --build
    if args.build == True:

        check_dockermachine_exists_and_running()

        # create a client to connect to docker-machine and use docker to manage containers
        client = docker.from_env(assert_hostname=False)
        
        # make base docker file
        dockerfile_arr = file_lines(args.image)

        # append spec dependences to docker file
        dockerfile_arr = append_build_require_to_docker_file(dockerfile_arr)

        # remove image before creating it
        remove_existing_docker_images(client)

        # preparing the dockerfile as string to be passed to the container as POST
        dockerfile = "".join(dockerfile_arr)
        file = BytesIO(dockerfile.encode('utf-8'))

        # create an image with docker filer
        create_docker_image(client,file)
        
        # removing the container first.
        remove_existing_docker_containers(client)

        # creating a container 
        container=create_docker_container(client)
 
        # start the container
        print '\n - starting container... \n'
        client.start(container)

        # create a tarfile for rpmbuild because the docker api only accepts tar files =/
        filedata = create_rpmbuild_tar(client,container)

        # transfer the rpmbuild tar to the container
        transfer_tar_to_container(client,container,filedata,'/root/')

        # remover rpmbuild tar
        remove_rpmbuild_tar("rpmbuild.tar")

        # we have to create a new instance of client because it raises a "Hijack is incompatible with use of CloseNotifier"
        client2 = docker.from_env(assert_hostname=False)
        
        # get the id of the execution and realizes it
        container_exec = build_rpm(client2,container)

        # start and print the execution of a command inside the running container
        rpmbuild_log = client2.exec_start(exec_id=container_exec['Id'])

        # print more logs if debug is passed as parameter
	if args.build == True:
	    print rpmbuild_log
	
        # get the tar file of the rpm and srpm from container
        tf = get_rpm_from_container(client2,container)

        # extract the tarfile of the folder generated with the rpm and srpm
	tf.extractall()

	print '\n - build complete! \n'

    # Test install: package-builder --test
    if args.test == True:
        # create a client to connect to docker-machine and use docker to manage containers
        client = docker.from_env(assert_hostname=False)

        # make base docker file
        dockerfile_arr = file_lines(args.image)

        # append spec dependences to docker file
        dockerfile_arr = append_build_require_to_docker_file(dockerfile_arr)

        # remove image before creating it
        remove_existing_docker_images(client)

        # preparing the dockerfile as string to be passed to the container as POST
        dockerfile = "".join(dockerfile_arr)
        file = BytesIO(dockerfile.encode('utf-8'))

        # create an image with docker filer
        create_docker_image(client,file)

        # removing the container first.
        remove_existing_docker_containers(client)

        # creating a container
        container=create_docker_container(client)

        # start the container
        print '\n - starting container... \n'
        client.start(container)

        # create a tarfile for rpmbuild because the docker api only accepts tar files =/
        filedata = create_rpms_tar(client, container)

        transfer_tar_to_container(client,container,filedata,'/root/rpmbuild/')

        # remover rpmbuild tar
        remove_rpmbuild_tar("rpms.tar")

	print '\n - now execute the following command: eval $(docker-machine env); docker exec -it package-builder /bin/bash\n'
	print '\n - when loggued into container, run: rpm -i /root/rpmbuild/RPMS/<architecture>/<name-of-the-rpm>.rpm\n'

if __name__ == '__main__':
    main()
