#! /usr/bin/env python
# -*- coding: utf-8 -*-

import time
import yum
import shutil
import docker as docker_client
import os
#import os.path
import argparse
import subprocess
from   subprocess import Popen, PIPE
import sys
import dockerpty
import platform
from   io import BytesIO
import tarfile
import StringIO

def get_spec(args_spec,pb_tmp_dir):
    if args_spec != '':
        spec_file = args_spec
    else:
        spec_file = './%s/rpmbuild/SPECS/spec' % pb_tmp_dir
    if os.path.isfile(spec_file) == False:
        raise ValueError("The spec file %s wasnt found" % spec_file)
    else:
        print '\n - using spec file: %s... \n' % spec_file
    return spec_file

def get_source(args_source,pb_tmp_dir):
    if args_source != '':
        source_file = args_source
        if os.path.isfile(source_file) == False:
            raise ValueError("The source file %s wasnt found" % source_file)
	else:
	    print '\n - using source file %s\n' % source_file
    else:
        source_file = ''
        source_dir = "./%s/rpmbuild/SOURCES" % pb_tmp_dir
        ls = os.listdir(source_dir)
        spec_file_name = filter(lambda x:'tar.gz' in x, ls)
        if len(spec_file_name) == 0:
            raise ValueError("No source file was found on: %s" % source_dir)
	else:
	    source_file = "./%s/rpmbuild/SOURCES/%s" % (pb_tmp_dir,spec_file_name[0])
            print '\n - using source file: %s... \n' % source_file
    return source_file

def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))

def file_lines(docker_image):
    print '\n - using docker image: %s... \n' % docker_image
    lines = [        
        "FROM %s\n" % (docker_image),
        'RUN yum install rpmdevtools wget -y\n',
        'RUN yum groupinstall "Development Tools" -y\n',
        'RUN rpmdev-setuptree\n',
    ]    
    return lines

def get_spec_file_name(pb_tmp_dir):
    ls = os.listdir("./%s/rpmbuild/SPECS" % pb_tmp_dir)
    spec_file_name = filter(lambda x:'spec' in x, ls)
    if len(spec_file_name) == 0:
        raise ValueError("No spec file was found on: %s" % os.getcwd())
    print '\n - using spec file: %s... \n' % spec_file_name[0]
    return spec_file_name[0]

def make_build_require_list(spec_file):
    with open(spec_file, "r") as spec:
        spec_lines = spec.readlines()
    build_requires = filter(lambda x:'BuildRequires' in x, spec_lines)
    build_require_list = []
    for i in build_requires:
        build_file = i.split()[1]
        build_require_list.append(build_file)
    return build_require_list

#def make_source_list(spec_file):
#    with open(spec_file, "r") as spec:
#        spec_lines = spec.readlines()
#    sources = filter(lambda x:'Source' in x, spec_lines)
#    source_list = []
#    for i in sources:
#        source_file = i.split()[1]
#        source_list.append(source_file)
#    return source_list

def append_build_require_to_docker_file(dockerfile,spec_file):
    for i in make_build_require_list(spec_file):
        file_line = "RUN yum install -y %s\n" % (i,)
        dockerfile.append(file_line)
    return dockerfile

def get_docker_host(system):
    if system == 'mac':
        shellinit = os.popen("docker-machine url package-builder").read()
        print '\n - using docker-machine %s\n' % shellinit.strip()
    elif system == 'linux':
        shellinit = "tcp://0.0.0.0:2375"
    else:
        raise ValueError("system not suported yet")
    return shellinit.strip()

def check_system():
    osplatform = platform.system()
    if osplatform == 'Darwin':
        system = "mac"
    elif osplatform == 'Linux': 
        system = "linux"
    else:
        raise ValueError("system not suported yet")
    return system

def install_docker(system):
    if system == 'mac':
        # Verifies that docker-machine is installed
        cmd = ['/usr/local/bin/docker-machine']
        FNULL = open(os.devnull, 'w')
        returncode = subprocess.Popen(cmd,stdout=FNULL).wait()
        if returncode != 0:
            print '\n - instaling docker-machine ...\n'
            if os.system("brew cask list dockertoolbox") != 0:
                os.system("brew update") # It had raised an ruby error so I had to update brew first
                os.system("brew install Caskroom/cask/dockertoolbox") 
        returncode = subprocess.Popen(cmd,stdout=FNULL).wait()
        if returncode != 0:
            print "Could not find or install docker machine. Please verify if the docker-machine installation was succeded "
            sys.exit(1)
    
        # Verifies that the docker vm called package-builder exists
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
    elif system == 'linux':
        yb = yum.YumBase()
        if yb.rpmdb.searchNevra(name='docker-engine'):
            print ('\n - docker is installed...\n')
            returncode = os.system("pgrep docker > /dev/null")
            if returncode != 0:
                print ('\n - docker is not running...\n')
                print ('\n - starting docker daemon on tcp://0.0.0.0:2375\n')
                os.system("docker daemon -H tcp://0.0.0.0:2375 > /dev/null &")
            else:
                print ('\n - docker is running...\n')
        else:
            print ('\n - docker is not installed...\n')
            returncode = os.system("yum install docker-engine -y")
            if returncode != 0:
                print ('failed to install docker-engine. Please check the errors above')
                print ('Maybe you have to add docker yum repo first:')
                print ("sudo tee /etc/yum.repos.d/docker.repo <<-'EOF'")
                print ("[dockerrepo]")
                print ("name=Docker Repository")
                print ("baseurl=https://yum.dockerproject.org/repo/main/centos/$releasever/")
                print ("enabled=1")
                print ("gpgcheck=1")
                print ("gpgkey=https://yum.dockerproject.org/gpg")
                print ("EOF")
                sys.exit(1) 
            else:
                print ('\n - starting docker daemon on 0.0.0.0:2375\n')
                os.system("nohup docker daemon -H tcp://0.0.0.0:2375 &")
    else:
        raise ValueError("system not suported yet")

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
    #containers_to_remove = client.containers(all=True, filters={'Names': 'package-builder'})
    containers_to_remove = client.containers(all=True, filters={'name': 'package-builder'})
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

def create_rpmbuild_tar(client, container, spec_file, source_file, pb_tmp_dir):
    print '\n - creating a tarfile of rpmbuild folder to transfer it to the container... \n'
    spec_dir='%s/rpmbuild/SPECS' % pb_tmp_dir
    source_dir='%s/rpmbuild/SOURCES' % pb_tmp_dir
    if not os.path.exists(spec_dir):
        os.makedirs(spec_dir)
    shutil.copy2(spec_file, spec_dir)
    if not os.path.exists(source_dir):
        os.makedirs(source_dir)
    if source_file != '':
        shutil.copy2(source_file, source_dir)
    make_tarfile("rpmbuild.tar", "%s/rpmbuild" % pb_tmp_dir)
    f = open('rpmbuild.tar', 'rb')
    return f.read()

def create_rpms_tar(client, container, pb_tmp_dir):
    print '\n - creating a tarfile of rpm files to transfer it to the container... \n'
    make_tarfile("rpms.tar", "%s/rpmbuild/RPMS" % pb_tmp_dir)
    f = open('rpms.tar', 'rb')
    return f.read()

def remove_rpmbuild_tar(tarfile):
    print '\n - removing tarfile... \n'
    os.remove(tarfile)

def remove_rpmbuild_dir(rpmbuilddir):
    print '\n - removing rpmbuilddir %s \n' % rpmbuilddir
    if os.path.exists(rpmbuilddir):
         shutil.rmtree(rpmbuilddir)

def build_rpm(client,container,pb_tmp_dir):
    print '\n - building the rpm... \n'
    container_exec = client.exec_create(container=str(container['Id']), cmd='/bin/bash -c "/usr/bin/rpmbuild -ba /root/rpmbuild/SPECS/%s"' % get_spec_file_name(pb_tmp_dir), stdout=True, stderr=True, tty=True)
    return container_exec

def get_rpm_from_container(client,container):
    print '\n - getting srpm and rpm from the container... \n'
    stream, stats = client.get_archive(container=str(container['Id']), path='/root/rpmbuild')
    file_content = StringIO.StringIO(stream.read())
    tf = tarfile.open(fileobj=file_content)
    return tf

def connect_docker(system):
    tries = 0
    while tries < 3:
        try:
            docker = docker_client.Client(base_url=get_docker_host(system),timeout=3000,version='auto')
            break
        except Exception as e:
            print '\n - docker isnt running yet. Waiting... \n'
            time.sleep(1)
            tries += 1
    if tries == 3:
        raise ValueError("Could not verify that docker is running")
    return docker

def build(system,args_spec,args_source,args_image,pb_tmp_dir):
    # verify that docker-machine for mac or docker-engine for linux exists and it is running
    install_docker(system)
    # docker
    docker = connect_docker(system)
    # Set spec and source files
    spec_file = get_spec(args_spec,pb_tmp_dir)
    source_file = get_source(args_source,pb_tmp_dir)
    # remove rpmbuild dir
    remove_rpmbuild_dir('./%s' % pb_tmp_dir) 
    # create a client to connect to docker-machine and use docker to manage containers
    client = docker.from_env(assert_hostname=False)
    # make base docker file
    dockerfile_arr = file_lines(args_image)
    # append spec dependences to docker file
    dockerfile_arr = append_build_require_to_docker_file(dockerfile_arr, spec_file)
    print(dockerfile_arr)
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
    filedata = create_rpmbuild_tar(client,container,spec_file,source_file,pb_tmp_dir)
    # transfer the rpmbuild tar to the container
    transfer_tar_to_container(client,container,filedata,'/root/')
    # remover rpmbuild tar
    remove_rpmbuild_tar("rpmbuild.tar")
    # we have to create a new instance of client because it raises a "Hijack is incompatible with use of CloseNotifier"
    client2 = docker.from_env(assert_hostname=False)
    # get the id of the execution and realizes it
    container_exec = build_rpm(client2,container,pb_tmp_dir)
    # start and print the execution of a command inside the running container
    rpmbuild_log = client2.exec_start(exec_id=container_exec['Id'])
    # get the tar file of the rpm and srpm from container
    tf = get_rpm_from_container(client2,container)
    # extract the tarfile of the folder generated with the rpm and srpm
    tf.extractall(path='./%s/' % pb_tmp_dir)
    print '\n - build complete! \n'

def test(system,args_spec,args_source,args_image,pb_tmp_dir):
    # verify that docker-machine for mac or docker-engine for linux exists and it is running
    install_docker(system)
    # docker
    docker = connect_docker(system)
    # Set spec and source files 
    spec_file = get_spec(args_spec,pb_tmp_dir)
    source_file = get_source(args_source,pb_tmp_dir)
    # create a client to connect to docker-machine and use docker to manage containers
    client = docker.from_env(assert_hostname=False)
    # make base docker file
    dockerfile_arr = file_lines(args_image)
    # append spec dependences to docker file
    dockerfile_arr = append_build_require_to_docker_file(dockerfile_arr, spec_file)
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
    filedata = create_rpms_tar(client, container,pb_tmp_dir)
    # transfer the rpmbuild tar to the container
    transfer_tar_to_container(client,container,filedata,'/root/rpmbuild/')
    # remover rpmbuild tar
    remove_rpmbuild_tar("rpms.tar")

    print '\n - when loggued into container, run: rpm -i /root/rpmbuild/RPMS/<architecture>/<name-of-the-rpm>.rpm\n'

    if system == 'mac':
        os.system("eval $(docker-machine env package-builder); docker exec -it package-builder /bin/bash")
    elif system == 'linux':
        os.system("export DOCKER_HOST='tcp://0.0.0.0:2375'; docker exec -it package-builder /bin/bash -c \"echo 'To test the RPM, use rpm -i to install the RPMs below:'; find /root/rpmbuild -name *.rpm;/bin/bash\"")
    else:
        raise ValueError("system not suported yet")
    print '\n - stoping container... \n'
    client.stop(container)

def main():
    parser = argparse.ArgumentParser(prog='package-builder', description='Make loca enviroment to build OS packages with docker')
    parser.add_argument("-u", "--up", action="store_true", help="install and start local enviroment")
    parser.add_argument("-b", "--build", action="store_true", help="build OS package")
    parser.add_argument("-t", "--test", action="store_true", help="start shell with a clean container and copy package to test it") 
    parser.add_argument("-i", "--image", default='centos:centos7', help="docker image, default: centos:centos7, see the options in https://registry.hub.docker.com") 
    parser.add_argument("-d", "--debug", action="store_true", help='print more logs') 
    parser.add_argument("-s", "--spec", default='', help='specify a spec file') 
    parser.add_argument("-o", "--source", default='', help='specify a source .tar.gz file') 
    parser.add_argument("-n", "--session", default='', help='specify a temporary folder name') 

    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(1)

    # Without this we cant connect to docker via python even if the pass the base_url=HOST. Bizarre
    os.environ['DOCKER_HOST']='tcp://0.0.0.0:2375'
    args = parser.parse_args()
    system = check_system()

    if args.session != '':
        pb_tmp_dir = 'package_builder_tmp%s' % args.session
    else:
        pb_tmp_dir = 'package_builder_tmp'

    # Start: package-builder --up
    if args.up == True:
        install_docker(system)
    
    # Build: packege-builder --build
    if args.build == True:
        build(system,args.spec,args.source,args.image,pb_tmp_dir)

    # Test install: package-builder --test
    if args.test == True:
        test(system,args.spec,args.source,args.image,pb_tmp_dir)

if __name__ == '__main__':
    main()
