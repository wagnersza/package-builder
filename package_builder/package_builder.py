#! /usr/bin/env python
# -*- coding: utf-8 -*-

import docker as docker_client
import os
import argparse
import subprocess
import sys
import dockerpty
import platform
from io import BytesIO
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

#def make_docker_file_rpmbuild(docker_image):
#    file_lines_read = file_lines(docker_image)
#    with open("Dockerfile", 'w') as d_file:
#        d_file.writelines(file_lines_read)
        
def make_docker_file_default(docker_image):
    test_dir = './test'
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    file_lines_read = file_lines(docker_image)
    file_lines_list = file_lines_read[0]
    with open("./test/Dockerfile", 'w') as d_file:
        d_file.writelines(file_lines_list)

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

#def spec_file_line():
#    file_line = "COPY %s /rpmbuild/SPECS/\n" % (get_spec_file_name(),)
#    return file_line

def append_spec_file_to_docker_file(dockerfile):
    file_line = "COPY %s /rpmbuild/SPECS/\n" % (get_spec_file_name())
    #file_line = ""
    dockerfile.append(file_line)
    return dockerfile
#    with open('Dockerfile', 'a') as d_file:
#        spec_file = d_file.writelines(spec_file_line())

def append_build_require_to_docker_file(dockerfile):
    for i in make_build_require_list():
        file_line = "RUN yum install -y %s\n" % (i,)
        #with open('Dockerfile', 'a') as d_file:
        #    d_file.writelines(file_line)
        dockerfile.append(file_line)
    return dockerfile

def append_source_to_docker_file(dockerfile):
    for i in make_source_list():
        file_line = "ADD %s /rpmbuild/SOURCES/\n" % (i,)
        dockerfile.append(file_line)
    return dockerfile
#        with open('Dockerfile', 'a') as d_file:
#            d_file.writelines(file_line)

def get_docker_host():
    #shellinit = os.popen("docker-machine env | grep DOCKER_HOST | sed 's/export //g' | sed 's/\"//g'").read()
    shellinit = os.popen("docker-machine url").read()
    return shellinit.strip()

def get_docker_ip():
    #shellinit = os.popen("docker-machine env | grep DOCKER_HOST | sed 's/export //g' | sed 's/\"//g'").read()
    shellinit = os.popen("docker-machine ip").read()
    return shellinit.strip()

def install_docker():
    # print platform.system()
    if platform.system() == 'Darwin':
        print '\n - instaling docker-machine ...\n'
        if os.system("brew cask list dockertoolbox") != 0:
            os.system("brew update") # It had raised an ruby error so I had to update brew first
            os.system("brew install Caskroom/cask/dockertoolbox") 
        print '\n - starting docker-machine...\n'
        os.system("docker-machine start default")
#        print '\n - setting DOCKER_HOST env variable ...\n'
#        docker_host = get_docker_host()
#        os.environ['DOCKER_HOST'] = docker_host#; os.system('bash')
    else:
        print "system not suported yet"


def main():
    parser = argparse.ArgumentParser(prog='package-builder', description='Make loca enviroment to build OS packages with docker')
    parser.add_argument("-u", "--up", action="store_true", help="install and start local enviroment")
    parser.add_argument("-b", "--build", action="store_true", help="build OS package")
    parser.add_argument("-t", "--test", action="store_true", help="start shell with a clean container and copy package to test it") 
    parser.add_argument("-i", "--image", default='centos:centos7', help="docker image, default: centos:centos7, see the options in https://registry.hub.docker.com") 

    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    # docker
    docker = docker_client.Client(base_url=get_docker_host(),timeout=3000)

    # Start: package-builder --up
    if args.up == True:
        install_docker()
    
    # Build: packege-builder --build
    if args.build == True:
        # create a client to connect to docker-machine and use docker to manage containers
        #os.system("docker-machine env")
        client = docker.from_env(assert_hostname=False)
        
        # make base docker file
        #make_docker_file_rpmbuild(args.image)
        dockerfile_arr = file_lines(args.image)

        # append spec dependences to docker file
        dockerfile_arr = append_build_require_to_docker_file(dockerfile_arr)
        #dockerfile_arr = append_spec_file_to_docker_file(dockerfile_arr)
        # We have to copy SPEC file to container
        #dockerfile_arr = append_source_to_docker_file(dockerfile_arr)
        # build docker image

        #print dockerfile_arr
        #print dockerfile_arr
        dockerfile = "".join(dockerfile_arr)
        #print dockerfile
        f = BytesIO(dockerfile.encode('utf-8'))
        #print f
        client = docker.from_env(assert_hostname=False)
        # remove image before creating it
        print '\n - removing existing docker images with package-builder:base_build... \n'
        if len(client.images("package-builder:base_build")) != 0:
            client.remove_image("package-builder:base_build", force=True)
        else:
            print '\n - no docker images with name package-builder:base_build found to remove... \n'

        # create an image with docker filer
        print '\n - creating a new docker image as package-builder:base_build based on this Dockerfiler: \n'
        print dockerfile
        response = [line for line in client.build(
            fileobj=f,
            rm=True,
            tag='package-builder:base_build')
    #        custom_context=True,
    #        path=os.getcwd())
        ]
	#print response
        #print client.images()
        
        # removing the container first.
        print '\n - removing existing docker containers with package-builder name... \n'
        containers_to_remove = client.containers(all=True, filters={'Names': 'package-builder'})
        if len(containers_to_remove) != 0:
            client.remove_container(containers_to_remove[0]['Id'],force=True)
        else:
            print '\n - no containers with name package-builder found to remove... \n'

        # Creating a container 
        print '\n - creating a new docker container as package-builder... \n'
        container = client.create_container(
            name='package-builder',
            image='package-builder:base_build',
            stdin_open=True,
            tty=True,
            detach=False,
            command='bash'
            #command='/usr/bin/rpmbuild -ba /root/rpmbuild/SPECS/%s' % get_spec_file_name()
        )
 
        print '\n - starting container... \n'
        client.start(container)

        # create a tarfile for rpmbuild because the docker api only accepts tar files =/
        print '\n - creating a tarfile of rpmbuild folder to transfer it to the container... \n'
        make_tarfile("rpmbuild.tar", "rpmbuild")

        f = open('rpmbuild.tar', 'rb')
        filedata = f.read()
        print '\n - transfering the tarfile to the container ... \n'
        client.put_archive(container=str(container['Id']), path='/root/', data=filedata )
        print '\n - removing tarfile... \n'
        os.remove("rpmbuild.tar")

        # we have to create a new instance of client because it raises a "Hijack is incompatible with use of CloseNotifier"
        client2 = docker.from_env(assert_hostname=False)
        
        # get the id of the execution and realizes it
	print '\n - building the rpm... \n'
        container_exec = client2.exec_create(container=str(container['Id']), cmd='/bin/bash -c "/usr/bin/rpmbuild -ba /root/%s; find /root/rpmbuild/"' % get_spec_file_name(), stdout=True, stderr=True, tty=True)

        # start and print the execution of a command inside the running container
        print client2.exec_start(exec_id=container_exec['Id'])
	
	print '\n - getting srpm and rpm from the container... \n'
	stream, stats = client2.get_archive(container=str(container['Id']), path='/root/rpmbuild')

	file_content = StringIO.StringIO(stream.read())
	tf = tarfile.open(fileobj=file_content)
	#tf.extractall(path='rpmbuild_compiled/')
	tf.extractall()

	print '\n - build complete! \n'

        #client.logs('package-builder', stdout=True, stderr=True)
        # theres a bug on docker and we need a new client
        #client = docker.from_env(assert_hostname=False)
        #dockerpty.start(client, container)
        #out_stream = client.attach(container=container, stdout=True, stderr=True, stream=True)
 
        #print out_stream
        
        #docker_container = client.containers(latest=True)
        #print docker_container
 

        #os.system('docker build --tag="package-builder:base_build" .')
        ## create container
        #container = docker.create_container(
        #    image='package-builder:base_build',
        #    stdin_open=True,
        #    tty=True,
        #    command='/usr/bin/rpmbuild -ba /rpmbuild/SPECS/%s' % (get_spec_file_name(),)
        #)
        #docker.start(container)
        #dockerpty.PseudoTerminal(docker, container).start()
        ## copy rpm to local directory
        #docker_container = docker.containers(latest=True)
        #container_id = docker_container[0]['Id']
        #package_path = '/rpmbuild/RPMS'
        #os.system('docker cp %s:/rpmbuild/RPMS .' % (container_id,))
        #os.system('docker cp %s:/rpmbuild/SRPMS .' % (container_id,))
    
    # Test install: package-builder --test
    if args.test == True:
        make_docker_file_default(args.image)
        os.system('scp -r -i ~/.ssh/id_boot2docker RPMS SRPMS docker@%s:~/' % (get_docker_ip(),))
        os.system('docker build --tag="package-builder:base" ./test')
        os.system('docker run -i -t -v /home/docker/RPMS:/RPMS -v /home/docker/SRPMS:/SRPMS package-builder:base /bin/bash')

if __name__ == '__main__':
    main()
