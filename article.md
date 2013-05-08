# Building Python Packages with Maven

As a new engineer at Urban Airship, one of my first tasks was to
improve our build process for generated Python code. Specifically, a
number of internal projects use [Maven](http://maven.apache.org) to
generate Java and Python bindings from specifications written in
Google's [Protocol
Buffers](https://developers.google.com/protocol-buffers/) language.

Initially, our existing Maven projects executed Google's `protoc`
compiler and placed the generated code in a sub-directory of the
current project. The resulting code was then copied to various other
locations as needed. After I finished updating them, our Maven projects
created a Python package containing the generated bindings, with a
version matching that specified by the Maven project file, ready to upload to our
internal package distribution server. This article describes how I did
it.

Source files referenced in this article can be found in the [source
repository on
GitHub](https://github.com/urbanairship/mvn-python-packaging). The
version of the code matching the published version of this article is
tagged "`published`." All source file references will be relative
to the root of the git repository.

To execute the sample project, use the following command. The "Using
Profiles to Disable Packaging" section explains the reason for the
PYTHON_BINDINGS argument:

    mvn clean install -DPYTHON_BINDINGS

After Maven runs, you will find a Python package named
`sample-0.0.1.preview.tar.gz` in
`target/generated-sources/python/sample_pb/dist`. You will also find
the source for the package in `target/generated-sources/python`.

## Project Structure

The project contains the following files and directories:

  * `pom.xml` --- Maven project file.
  * `src/main/resources` --- Directory containing resources used to
  generate Python and Java sources. These include the Protocol Buffer
  definition, `sample.proto`, and several Python source files.

When Maven executes, all outputs are placed under the `target`
directory. These include generated Java sources, Java class and JAR
files, generated Python sources, and the Python package. We do not put
these files under version control, as they are never modified by
hand. Instead, they can be deleted and regenerated as needed.

## Maven Properties

I define several properties in `pom.xml` that configure how the Python
package gets built. These include:

  * `python_package` --- The name of the package to build (in this
    case, "sample_pb").
  * `author`, `author_email`, `description`, `source_url` ---
    Authorship and documentation.
  * `python_compile_phase` --- Discussed in the "Using Profiles to
    Disable Packaging" section.
 
# Generating Protocol Buffer Bindings

The project generates Python and Java sources from Protocol Buffer
definitions using Google's [`protoc`
compiler](https://code.google.com/p/protobuf/downloads/list). I used
the [`exec` plugin](http://mojo.codehaus.org/exec-maven-plugin/) to
execute `protoc` during the `generate-sources` phase. The following
snippet shows how the project executes `protoc`:

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
              <argument>
    --python_out=${project.build.directory}/generated-sources/python/${python_package}
              </argument>
              <argument>${basedir}/src/main/resources/*.proto</argument>
            </arguments>
          </configuration>
        </execution>
      ...

The `--python_out` argument specifies where generated Python source
goes; in the above, `${project.build.directory}/generated-sources`
ensures that generated code gets placed under the `target/generated-sources`
directory. The `python/${python_package}` portion of the path puts the
generated code in the `python/sample_pb` directory, just where I need
it in order to include it in a package. The section "Building the
Package" describes how I create a package from the generated source.

## Package Metadata

The source from which a given package is built can take a number of
forms; for this project, I used the conventions given by
[`setuptools`](http://peak.telecommunity.com/DevCenter/setuptools). A
top-level directory (in this case, `target/generated-sources/python`)
contains three files: `MANIFEST.in`, `setup.py`, and
`requirements.txt`. Files making up the package, including
`__init__.py`, are in a sub-directory named after
the package, `sample_pb`.

Excepting `requirements.txt`, each of these files contains specific
information about the package that may change with each build. For
example, `__init__.py` specifies a version number that should be the
same as that in `pom.xml`. Because these files can change on each
build --- and they are not automatically generated --- I used Maven's
"[filtered
resources](http://maven.apache.org/guides/getting-started/index.html#How_do_I_filter_resource_files)"
to create them.

Maven defines resources as files that are included in your project
before compilation, but are not compiled themselves. Resources are
typically stored in `src/main/resources` and copied to another
location within the project before compilation. Maven can also
"filter" these files, by performing a simple find-and-replace
operation on their contents, before copying them. Thus, "filtered
resources."

Therefore, I placed `MANIFEST.in`, `setup.py`, `requirements.txt` and
`__init__.py` in `src/main/resources`. I defined a `<resources>`
section in `pom.xml` that specifies the destination for each file. For
example, `__init__.py` must be copied to
`target/generated-sources/python/sample_pb`.  The `<targetPath>`
element ensures the file ends up in the right place:

    <resource>
      ...
        <include>__init__.py</include>
      ...
      <targetPath>
    ${project.build.directory}/generated-sources/python/${python_package}
      </targetPath>
      ...
    </resource>

The files `MANIFEST.in`, `setup.py`, etc. are actully templates
containing references to Maven properties that will be replaced with
their actual value when the file is copied to its final
destination. For example, `MANIFEST.in` has these two lines:

    include requirements.txt
    include ${python_package}/*.proto

The text "`${python_package}`" will be replaced by the value of the
`python_package` property, as specified in `pom.xml`. When Maven
copies this file to `target/generated-sources/python`, it will have these
contents:

    include requirements.txt
    include sample_pb/*.proto

Similar replacements occur with `__init__.py` and `setup.py`. 

## Package Version Numbering

Our projects adhere to Java conventions, where "pre-release" libraries
have the word "SNAPSHOT" appended to their version number; this
project would be "0.0.1-SNAPSHOT." Following `setuptools`
[recommendation](http://peak.telecommunity.com/DevCenter/setuptools#specifying-your-project-s-version),
I choose to translate "SNAPSHOT" versions into corresponding "preview"
versions. That is, "0.0.1-SNAPSHOT" becomes "0.0.1.preview"; just the
numeric version number is used for released versions of a package.

`pom.xml` already specifes a value for the project version (in the
`<version>` element) and I wanted the Python package to have the same
version. In order to do so, I used the `regex-property` goal provided
by the [build
helper](http://mojo.codehaus.org/build-helper-maven-plugin/)
plugin. This goal will assign a given property the result of applying
a regular expression to an input value. Below, you can see the
execution I defined to transform version numbers:

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

Essentially, I replace occurrences of "`-SNAPSHOT`" in the property
`project.version` with "`.preview`" and assign the result to the
property `python_version`. 

`__init__.py` and `setup.py` (in `src/main/resources`) both
refer to the `python_version` property. Here is `__init__.py`:

    __version__ = '${python_version}'

and `setup.py`:

    setup(
        ...
        version='${python_version}',
        ...
    )

When Maven filters and copies these files, `${python_version}` will be
replaced with the correct version for the build. Because `pom.xml`
sets the version to `0.0.1-SNAPSHOT`, `__init__.py` ends up with these
contents (and `setup.py` is rewritten similarly):

    __version__ = '0.0.1.preview'

Even better, when a Maven "release" build is performed,
`__init__py` becomes:

    __version__ = '0.0.1'

This ensures that the version
number of the Python package always matches that found in `pom.xml`.

## Building the Package

Python builds the package (via the `exec` plugin) by
executing `setup.py` in `target/generated-sources/python` with an
`sdist` argument:

    <execution>
      <id>generate-package</id>
      <phase>compile</phase>
      <goals>
        <goal>exec</goal>
      </goals>
      <configuration>
        <executable>python</executable>
        <workingDirectory>
    ${project.build.directory}/generated-sources/python
        </workingDirectory>
        <arguments>
          <argument>setup.py</argument>
          <argument>sdist</argument>
        </arguments>
      </configuration>
    </execution>

This configuration is attached to the `compile` phase, which means it
will fire after all resources have been filtered and written to
`target/generated-sources/python`. In other words, the metadata
specified by `setup.py`, `__init__.py`, and the other files will match
whatever is specified in `pom.xml`.

# Using Profiles to Disable Packaging

When I released this project internally, I immediately heard from
other developers that I had introduced a Python dependency into
their development environment. That wasn't acceptable to developers
who didn't care about the generated Python bindings. I could not back
these changes out entirely, because we wanted these packages to be
built on our CI server, and we wanted the packages to stay in the same
project as the Protocol Buffer definitions.  In effect, I wanted 
the Python package to be built in only three circumstances:

  * When I was developing
  * When someone wanted to do a one-time build
  * When building the package on the CI server

Maven [profiles](http://maven.apache.org/pom.html#Profiles) are
designed to address this situation. A profile can specify certain
conditions which, when met, add new settings and configurations to the
project. 

I started using profiles but quickly found myself repeating large
chunks of configuration. Each profile can only match one
condition. Therefore, for the three conditions above, I needed to
repeat the same configuration. I wanted a better solution.

In the previous section, I showed a configuration that executed Python
during the `compile` phase, but in truth that is not quite
correct. The actual definition that specifies how to execute Python
then uses a property in the `<phase>` element, rather than a fixed
value:

     <execution>
       <id>generate-package</id>
       <phase>${python_compile_phase}</phase>
       <goals>
         <goal>exec</goal>
       </goals>
      <configuration>
        <executable>python</executable>
        ...
      </configuration>
     </execution>

`python_compile_phase` is initially set to `never` --- a non-existent
phase. If the property value doesn't change, then `python` will not
execute, because the `never` phase won't occur! I then defined
profiles that changed the value of `python_compile_phase` to `compile`
when certain command line flags or environment variables were
found. For example, this profile looks for `-DPYTHON_BINDINGS` on the
command-line:

    <id>python-builder</id>
    <activation>
      <property>
        <name>PYTHON_BINDINGS</name>
      </property>
    </activation>
    <properties>
      <python_compile_phase>compile</python_compile_phase>
    </properties>

Similar profiles look for environment variables named `PYTHON_BINDINGS`
and `JENKINS_URL` (which indicates we are building on the CI server).

With this solution, I met my three goals. I could set the enviroment
variable `PYTHON_BINDINGS` on my local machine and always build
packages. If a developer wanted to build the packages once, they could
given Maven the `-DPYTHON_BINDINGS` command-line argument. On our CI
server, `JENKINS_URL` will always be defined, so Python packages are
built. Finally, developers that don't opt-in will see no changes 
whatsoever --- the packages are just never built.

# Future Improvements

I implemented the scheme described here over the course of several
weeks and multiple projects. By the end, I had found a way to define
properties in `pom.xml` such that I only needed to copy boilerplate
files between projects (specifically, the four files in
`src/main/resources`). Otherwise, I just modified `pom.xml` for the
specific project. However, every time I found a way to improve this
system, I had to update multiple projects. A Maven plugin that handles
these tasks is an obvious next step.

The solution given here depends on a functioning Python installation,
including the right version of Google's Protocol Buffers package for
Python. A way for Maven to download (and verify) the correct packages
would help make the solution more robust.

Finally, I am not sure how future-proof it is to use a build phase that 
doesn't exist. It doesn't cause an error now, but in the future I'm not 
sure. Maybe it would be worth asking the Maven project to add a build
phase that never executes, just for this purpose?

