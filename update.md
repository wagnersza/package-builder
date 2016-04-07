colocar os passos de instalacao de virtualenv e criacao do virtualenv package-builder
workon package-builder

./package_builder.py -b -i centos:centos6

sh: boot2docker: command not found
Traceback (most recent call last):
  File "./package_builder.py", line 164, in <module>
    main()
  File "./package_builder.py", line 124, in main
    docker = docker_client.Client(base_url=get_docker_url(),timeout=3000)
  File "./package_builder.py", line 89, in get_docker_url
    return docker_url[1]
IndexError: list index out of range

brew update
brew install Caskroom/cask/dockertoolbox

docker-machine start default
