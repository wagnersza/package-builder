# package-builder

Builds OS packages inside a docker container. A Dockerfile and build context are dynamically generated to construct the package development environment. Then build command is executed and the build results are extracted.

After the build, you can test the package inside a new docker container only using the parameter --test.

> now is only suported for Mac OS, and RPM packages  
> suggestions, issues and pull requests are welcome.

## Install

```bash
$ pip install git+https://github.com/wagnersza/package-builder
```
## Prepare environment

Install and start a new boot2docker VM and prepares the package development environment

```bash
$ package-builder --start
```

## Build packages

The package-builder expects to be inside a directory that contains the spec file, 

It scans the package looking for sources, put inside the docker image and run the build command.

> the package-builder supports using the url of the source to automatically download into the container
> now package-builder don't convert spec variables, you must use the full name.  
> for instance:  
> not suported: Source0: http://meupacote.com/%{name}-%{version}.tar.gz  
> suported: Source0: http://meupacote.com/pacote-0.0.1.tar.gz  
> suported spec file example in https://github.com/wagnersza/tsuru-spec  

```bash
$ package-builder --build
```

## Test packages builded

Testing the generated package into a clean container

```bash
$ package-builder --test
```

> the packages can be found inside the directories /RPM and /SRPM

## Select Docker image to build a package

Now by default package-builder uses centos:centos7 image, but can changed using  
the parameter --image

> see the options in https://registry.hub.docker.com

```bash
$ package-builder --image <docker image>
```
