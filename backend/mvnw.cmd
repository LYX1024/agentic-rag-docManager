@REM ----------------------------------------------------------------------------
@REM Maven Wrapper startup script for Windows
@REM ----------------------------------------------------------------------------

@if "%DEBUG%"=="" @echo off
@setlocal

set MAVEN_PROJECTBASEDIR=%CD%
set MAVEN_OPTS=-Xmx512m

if not "%JAVA_HOME%"=="" (
  set JAVA_EXE="%JAVA_HOME%\bin\java.exe"
) else (
  set JAVA_EXE=java
)

%JAVA_EXE% -classpath "%MAVEN_PROJECTBASEDIR%\.mvn\wrapper\maven-wrapper.jar" ^
  -Dmaven.multiModuleProjectDirectory="%MAVEN_PROJECTBASEDIR%" ^
  org.apache.maven.wrapper.MavenWrapperMain %*

@endlocal
