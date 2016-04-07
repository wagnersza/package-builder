#! /usr/bin/env python
# -*- coding: utf-8 -*-

import docker as docker_client
import os
import argparse
import subprocess
import sys
import dockerpty
import platform

def file_lines(docker_image):
    lines = [        
        "FROM %s\n" % (docker_image),
        'RUN yum install rpmdevtools wget -y\n',
        'RUN yum groupinstall "Development Tools" -y\n',
        'RUN rpmdev-setuptree\n',
    ]    
    return lines

def make_docker_file_rpmbuild(docker_image):
    file_lines_read = file_lines(docker_image)
    with open("Dockerfile", 'w') as d_file:
        d_file.writelines(file_lines_read)
        
def make_docker_file_default(docker_image):
    test_dir = './test'
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    file_lines_read = file_lines(docker_image)
    file_lines_list = file_lines_read[0]
    with open("./test/Dockerfile", 'w') as d_file:
        d_file.writelines(file_lines_list)

def get_spec_file_name():
    ls = os.listdir(".")
    spec_file_name = filter(lambda x:'spec' in x, ls)
    return spec_file_name[0]

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

def spec_file_line():
    file_line = "COPY %s /rpmbuild/SPECS/\n" % (get_spec_file_name(),)
    return file_line

def append_spec_file_to_docker_file():
    with open('Dockerfile', 'a') as d_file:
        spec_file = d_file.writelines(spec_file_line())

def append_build_require_to_docker_file():
    for i in make_build_require_list():
        file_line = "RUN yum install -y %s\n" % (i,)
        with open('Dockerfile', 'a') as d_file:
            d_file.writelines(file_line)

def append_source_to_docker_file():
    for i in make_source_list():
        file_line = "ADD %s /rpmbuild/SOURCES/\n" % (i,)
        with open('Dockerfile', 'a') as d_file:
            d_file.writelines(file_line)

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
            os.system("brew update") 
            os.system("brew install Caskroom/cask/dockertoolbox") # Ele gerou um erro de ruby. So resolvi atualizando o brew acima
        print '\n - starting docker-machine...\n'
        os.system("docker-machine start default")
        print '\n - setting DOCKER_HOST env variable ...\n'
        docker_host = get_docker_host()
        os.environ['DOCKER_HOST'] = docker_host#; os.system('bash')
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
        # make base docker file
        make_docker_file_rpmbuild(args.image)
        # append spec dependences to docker file
        append_build_require_to_docker_file()
        append_spec_file_to_docker_file()
        append_source_to_docker_file()
        # build docker image
        os.system('docker build --tag="package-builder:base_build" .')
        # create container
        container = docker.create_container(
            image='package-builder:base_build',
            stdin_open=True,
            tty=True,
            command='/usr/bin/rpmbuild -ba /rpmbuild/SPECS/%s' % (get_spec_file_name(),)
        )
        docker.start(container)
        dockerpty.PseudoTerminal(docker, container).start()
        # copy rpm to local directory
        docker_container = docker.containers(latest=True)
        container_id = docker_container[0]['Id']
        package_path = '/rpmbuild/RPMS'
        os.system('docker cp %s:/rpmbuild/RPMS .' % (container_id,))
        os.system('docker cp %s:/rpmbuild/SRPMS .' % (container_id,))
    
    # Test install: package-builder --test
    if args.test == True:
        make_docker_file_default(args.image)
        os.system('scp -r -i ~/.ssh/id_boot2docker RPMS SRPMS docker@%s:~/' % (get_docker_ip(),))
        os.system('docker build --tag="package-builder:base" ./test')
        os.system('docker run -i -t -v /home/docker/RPMS:/RPMS -v /home/docker/SRPMS:/SRPMS package-builder:base /bin/bash')

if __name__ == '__main__':
    main()
