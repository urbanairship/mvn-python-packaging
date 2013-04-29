# Building Python Packages with Maven

As a new engineer at Urban Airship, one of my first tasks was to
improve our build process for generated python code. Specifically, a
number of internal projects use (Maven)[http://maven.apache.org] to
generate bindings in multiple languages (Java, Python, etc.) that can
produce and consume messages described by Google's
(Protobuf)[TODO protobuf URL] language.

When I started, the existing maven projects executed Google's `protoc`
compiler and placed the generated code in a sub-directory of the
current project. The resulting code was then copied to various other
projects, as needed. When I finished, our maven projects created a
python package containing the generated bindings, with a version
matching the corresponding Java JAR file, ready to upload to our
internal python packag distribution server. This article will describe
what I did to build these packages using Maven.

(TODO: Describe why I generalized the maven configuration below).

Source files referenced in this article can be found in the (source
repository on GitHub)[TODO: GitHub URL]. The version of the code
matching the published version of this article is tagged 'TODO: tag
source'. All source file references will be relative to the git
repository.

To execute the sample project, use the following invocation:

    mvn clean install -DPYTHON_BINDINGS

The ``Using Profiles to Disable Packaging'' section explains the reason
for the PYTHON_BINDINGS argumetn.

## Project Structure

I structured the sample project for this article according to maven
conventions. The project contains the following files
and directories:

  * pom.xml -- A maven project file.
  * src/main/java -- Directory containing all Java source code.
  * src/main/python -- Directory containing all python source code.
  * src/main/resources -- Directory containing static resources used
  to build the project.

Normally, all compiled code is placed under the `target` directory. However,
this project really generates **source** code, so our generated code
ends up under `src/main/java` and `src/main/python`.

## Python Packages

A python package consists of a collection of a single top-level
directory containing some number of Python source files, any number of
sub-directories, and a file named `__init__.py`.

The source from which a given package is built can take a number of
forms; for this project, I used the conventions given by
`setuptools`. In particular, the files for the package are stored in a
sub-directory named after the package (`sample_pb`). A top-level
directory contains three files: `MANIFEST.in`, `setup.py`, and
`requirements.txt`. Those three files, plus the `sample_pb`
sub-directory, are all that is needed to build and distribute the
`sample_pb` package.

## Project Properties

I defined several properties to configure the Python package that 
gets built. These include:

  * python_package -- The name of the package to build (in this case, ``sample_pb'').
  * author, author_email, description, source_ourl -- Authorship and documentation.

I also defined two other properties (`python_compile_phase` and
`python_deploy_phase`), which I will discuss later, in the section
``Using Profiles to Disable Packaging.''

# Building the Package

The project generates Python and Java sources using Google's `protoc`
compiler. I used the (`exec` plugin)[TODO: exec link] to execute
`protoc`, and execute it during `generate-sources` phase, as later
phases will actually take the source code and turn it into a Python
package or a JAR file. The following snippet shows how the project
executes `protoc`:

    <plugin>
      <artifactId>exec-maven-plugin</artifactId>
      ...
        <execution>
          ...
          <phase>generate-sources</phase>
          <goals><goal>exec</goal></goals>
          <configuration>
            <executable>protoc</executable>
            ...
            <arguments>
              ...
              <argument>--python_out=${basedir}/src/main/python/${python_package}</argument>
              <argument>${basedir}/src/main/resources/*.proto</argument>
            </arguments>
          </configuration>
        </execution>
      ...

`protoc` uses the `--python_out` argument to specify where generated
Python source goes; in the above, I used the `python_package` property
to make sure generated code gets placed in the `sample_pb` 
directory. In other words, `protoc` puts the generated code just
where I need it in order to build a package.

## Package Metadata

Metadata about the package comes from three files that should be in
the `src/main/python` directory: `MANIFEST.in`, `setup.py`, and
`_version.py`. Each of these files contains specific information about
the package that may change with each build. For example,
`_version.py` should match the version that appears in `pom.xml`. Because
these files (potentially) can change on each build (and they are not 
automatically generated), I used maven's ``(filtered resources)[TODO:
link to filtered resources)'' to create them.

Maven defines resources as files that are included in your project before
compilation, but are not compiled themselves. Resources are typically 
stored in `src/main/resources` and copied to another location within the
project before compilation. Maven can also ``filter'' these files, by 
performing a simple find-and-replace operation on their contents, before
copying them. Thus, ``filtered resources.''

Therefore, I placed `MANIFEST.in`, `setup.py` and `_version.py` in
`src/main/resources`. I defined a `<resources>` section in `pom.xml`
that copies them to their final location in `src/main/python` before
the Python package gets built. The files in `src/main/resources` 
include placeholder text so that maven can insert
text at build time. For example, `MANIFEST.in` has
these three lines:

    include requirements.txt
    include ${python_package}/*.proto
    include ${python_package}/_version.py

The text ```${python_package}`''(TODO: check spacing here) will
be replaced by the value of the `python_package` property, as specified in
`pom.xml`. When maven copies this file to `src/main/python`, it will end up
with these contents:

    include requirements.txt
    include sample_pb/*.proto
    include sample_pb/_version.py

Similar replacements occur with `_version.py` and `setup.py`.

## Package Version Numbering

Our java projects follow a versioning scheme where ``pre-release'' libraries have
the word ``SNAPSHOT'' appended to their version number. For example, this project
would be ``0.0.1-SNAPSHOT.'' (`setuptools`)[TODO: link to version number discussion]
recommends a different scheme, using both numeric versions and various alphabetic 
conventions to indicate different versions of a package. For this project, I choose
to translagte 'SNAPSHOT' versions into corresponding '.preview' versions. E.g., ``0.0.1-SNAPSHOT''
becomes  ``0.0.1.preview''; for released versions of a package, just the numeric 
version number is used.

`pom.xml` already defines a project version; I wanted to base the
version of the Python package on that version. In order to do so, I
used the `regex-property` goal provided by the (build helper)[TODO:
link to build helper] plugin. This goal will assign to a given
property the result of applying a regular expression to an input value. Below, you
can see the execution I defined to transform version numbers:

    <plugin>
      <groupId>org.codehaus.mojo</groupId>
      <artifactId>build-helper-maven-plugin</artifactId>
      ...
      <executions>
        <execution>
          <goals><goal>regex-property</goal></goals>
          <phase>generate-resources</phase>
          <configuration>
            <name>python_version</name>
            <regex>-SNAPSHOT</regex>
            <value>${project.version}</value>
            <replacement>\.preview</replacement>
            <failIfNoMatch>false</failIfNoMatch>
          </configuration>
        </execution>
      </executions>
    </plugin>

After execution, a property named `python_version` will exist,
containing the appropriate Python version (based on the given project
version). `_version.py`  (in `src/main/resources`) has these contents:

    __version__ = version = '${python_version}'

When maven copies (and filters) this file, `${python_version} will be
replaced with the correct version for this build. For example, because
`pom.xml` sets the version to `0.0.1-SNAPSHOT`, `_version.py` ends
up with these contents:

    __version__ = version = '0.0.1.preview'

Even better, when a maven 'release' build is performed, the version
number loses the 'preview' portion and becomes:

    __version__ = version = '0.0.1'

This setup ensures that the version number of the python package
always matches that found in `pom.xml`. 

## Building the Package

To build the package, I again used the (`exec`)[TODO: exec URL]
plugin. Specifically, I execute `setup.py` (in `src/main/python`),
giving it an `sdist` argument:

    <execution>
      <id>generate-package</id>
      <phase>compile</phase>
      <goals>
        <goal>exec</goal>
      </goals>
      <configuration>
        <executable>python</executable>
        <workingDirectory>${basedir}/src/main/python</workingDirectory>
        <arguments>
          <argument>setup.py</argument>
          <argument>sdist</argument>
        </arguments>
      </configuration>
    </execution>

This configuration is attached to the `compile` phase, which means it will
fire after all resources have been copied (and filterd) from `src/main/resources`
into `src/main/python`. 

##  Cleaning

Maven's (`clean` plugin)[TODO: clean plugin URL] deletes files found
under the directory specified by the `outputDirectory` property
(normally, `target/classes`). The settings I specified to build the
python package put code in the `src/main/python` directory, but those
files should still be deletd when `clean` is executed; therefore,
I specified additional directories and files that should be
removed. However, I could not just delete everything under
`src/main/python/sample_pb`, as some files were **not** generated. In
particular, I did not want to delete `requirements.txt` or
`sample_pb/__init__.py`. By using `<exclude>` tags, I can keep the two
files I want and delete all others:

    <plugin>
      <artifactId>maven-clean-plugin</artifactId>
      ...
      <configuration>
        ...
            <directory>${basedir}/src/main/python</directory>
            <includes>
              <include>**/*</include>
              <include>*</include>
            </includes>
            <excludes>
              <exclude>requirements.txt</exclude>
              <exclude>${python_package}/__init__.py</exclude>
            </excludes>
            <followSymlinks>false</followSymlinks>
        ...
      </configuration>
    </plugin>


The notation `**/*` means to delete all files in all sub-directories,
recursively (except any excluded files). Therefore, all files except
the two specified are removed. As a side-effect, maven will not delete
non-empty directories, so by keeping `__init__.py`, the `sample_pb`
directory is also preserved.

# Using Profiles to Disable Packaging

When I first released a version of this project internally, I
immediately heard from other developers (who did not use the python
bindings), that I had introduced a python dependency into their local
builds. That wasn't acceptable to Java developers that only cared
about the generated java bindings (as they did not want to go through
setting up a new Python environment). However, I could not back these
changes out entirely (or move them to an independent proejct), because
we wanted these packages to be built on our CI server, and we wanted
the packages to stay in the same project as the protobuf definitions.
In effect, I wanted to the Python package to be built in three
circumstances:

  * When I was developing (always)
  * When someone wanted to do a one-time build
  * When building the package under Jenkins

Maven profiles are designed to address this situation. The developer can
specify certain conditions and, if those are met, then new settings (from the
profiles section) can be added to the project definition. The effect is similar
to conditionally inserting blocks of XML. 

I started using profiles but quickly found myself repeating large chunks
of configuration. Each profile can only match on one condition (an environment
variable, a command-line flag, and some others). Therefore, for the the three
conditions above, I needed to repeat the same configuration. It wasn't maintainable.

In the ``Building the Package'' section I stated that the
configuration shown was attached to the `compile` phase, but in truth
that is not quite correct. For this particular situation, the python
dependency only affected the build when the `compile` phase
executed. Otherwise, it made no difference. Therefore, instead of
using profiles to control the configuration, I used profiles to set a
property (`python_compile_phase`) that controlled the **build phase**
which the exec configuration was attached to:

     <execution>
       <id>generate-package</id>
       <phase>${python_compile_phase}</phase>
       <goals>
         <goal>exec</goal>
       </goals>
       ...
     </execution>

I initially set `python_compile_phase` to `never` (a non-existent
phase). With this value, execution never occurs, because the given
phase does not exist! I then define profiles to look for specific
command line flags (`-DPYTHON_BINDINGS`) or environment variables
(`JENKINS_URL` or `PYTHON_BINDINGS`). If any of those exist,
`python_compile_phase` is set to `compile`, and the execution occurs
during the proper phase. 

For example, this profile looks for
`JENKINS_URL` (so the package will be built on our CI server):

    <profile>
      <id>jenkins-builder</id>
      <activation>
        <property>
          <name>env.JENKINS_URL</name>
        </property>
      </activation>
      <properties>
        <python_compile_phase>compile</python_compile_phase>
      </properties>
    </profile>

With this solution, I met my three goals. I could set the enviroment
variable `PYTHON_BINDINGS` on my local machine and always build
packages. On our CI server, `JENKINS_URL` will always be defined and
packages are built. Developers that don't want to build packages
don't have to do anything new -- the packages are not built by default.

# Future Improvements

I implemented the scheme described here over the course of several weeks
and multiple projects. By the end, I had found a way to define properties
in `pom.xml` such that I only needed to copy boilerplate files between 
projects (specifically, `setup.py`, `MANIFEST.in` and `_version.py` in
`src/main/resources`). Otherwise, I just modified `pom.xml` for the
specific project. However, every time I found a way to improve this system, I
had to update multiple projects. A maven plugin that handled these tasks is
an obvious next step.

I also am not sure how future-proof it is to use a build phase that 
doesn't exist. It doesn't cause an error now, but in the future I'm not 
sure. Maybe it would be worth asking the Maven project to add a build
phase that never executes, just for this purpose?

