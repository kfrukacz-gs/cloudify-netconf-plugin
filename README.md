# cloudify-netconf-plugin
Cloudify plugin for serializing TOSCA node templates to netconf configuration.

Support:
* both version of netconf protocol from rfc6242.
* ssh based communication

Code for now does not support:
* conditional statements with dependencies capabilities available on hardware level,
* can be described only input structures for netconf, output(received structures from netconf) does not validated and not described in yaml blueprints.
* complicated structures with list of types can be described only as static(not dynamic) in sophisticated cases
* case when we have to different structures by some condition, like we send configuration that in case dhcp - contain only flag that we have dhcp configuration,
otherwise we have full structures that have described static connection. So if in description we have both fields, in first case we send empty values, so we need to have
2 node types/configurations for dhcp and for static

For check generation:
* install tools/setup.py and yttc from https://github.com/cloudify-cosmo/yttc
* xml to yaml: netconfxml2yaml.py cloudify-netconf-plugin/tools/examples/rpc.xml
* yaml to xml: yaml2netconfxml.py cloudify-netconf-plugin/tools/examples/rpc.yaml
* generate parent yaml blueprint for include:
  cd tools/examples
  yttc turing-machine.yang

Vyatta example is valid only for Brocade Vyatta Network OS 4.1 R2 and before run vyatta blueprint run as root on router:
* cd /usr/share/doc/openvpn/examples/sample-keys/
* bash gen-sample-keys.sh

Script name can be different and related to Brocade vRouter version.

## tags name conversions logic:
* ```a``` -> tag with name "a" and namespaces will be same as parent
* ```a@b``` -> tag with name "b" and namespace a
* ```_@@a``` -> attribute with name a and namespace will be same as parent
* ```_@a@b``` -> attribute with name b and namespace will be a
* ```_@@``` -> text content for tag
* ```_!_``` -> text will be inserted as xml to parent node

## examples of conversion

### list
from:
```
{
    "b": {
        "a": [1, 2, 3],
        "c": 4
    }
}
```
to:
```
<b>
    <a>1</a>
    <a>2</a>
    <a>3</a>
    <c>4</c>
</b>
```
### dict
from:
```
{
    "b": {
        "a": 1,
        "c": 2
    }
}
```
to:
```
<b>
    <a>1</a>
    <c>2</c>
</b>
```
### attributes
from:
```
{
    "b": {
        "_@@a": 1,
        "_@@": 2
    }
}
```
to:
```
<b a=1>
    2
</b>
```
### text value for tag with attibutes
from:
```
{
    "b@a": {
        "_@c@a": 1,
        "_@@": 2,
        "_@@g": 3
    }
}
```
to:
```
<b:a c:a=1 b:g=3>
    2
</b:a>
```

### text value for raw insert
from:
```
{
    "a": {
        "_!_": "<g><a></a><c></c><d></d></g>"
    }
}
```
to:
```
<a>
    <g>
        <a/>
        <c/>
        <d/>
    </g>
</a>
```

## Node description example
```

node_templates:
  some-implimentation:
    type: cloudify.netconf.nodes.xml_rpc
    properties:
      netconf_auth:
        user: <user on device>
        password: <password on device, optional>
        ip: <ip for device or list of ip's if have failback ip's>
        key_content: <private key content>
        port: <port for device, optional by default 830>
        store_logs: <store all communication logs, optional by default false>
      metadata:
        xmlns:
          _: <default namespace>
        capabilities:
          <list of capabilities, optional>
    interfaces:
      cloudify.interfaces.lifecycle:
        create: // can be create / configure / start / stop / delete
          inputs:
            lock:
              <list databased for lock, optional>
            back_database: <datebase to copy, optional>
            front_database: <database for copy, optional>
            strict_check: <ignore not critical errors in xml, optional>
            calls:
              - action: <action name for netconf>
                payload:
                  <dict for put to payload>
                save_to: <field name for save to runtime properties, optional>
                deep_error_check: <look deeply for errors, optional by default false>
```

## Node description example with xml template

### xml command list file part (template file)
```
<?xml version='1.0' encoding='UTF-8'?>
<rfc6020:rpc xmlns:rfc6020="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:xnm="http://xml.juniper.net/xnm/1.1/xnm" rfc6020:message-id="1001">
  <rpc-command-one/>
</rfc6020:rpc>]]>]]>

<?xml version='1.0' encoding='UTF-8'?>
<rfc6020:rpc xmlns:rfc6020="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:xnm="http://xml.juniper.net/xnm/1.1/xnm" rfc6020:message-id="1002">
  <rpc-command-two>
    {{ some_param_name }}
  </rpc-command-two>
</rfc6020:rpc>]]>]]>
```
As separator between commands must be used ```]]>]]>```

### yaml example part
```

node_templates:
  some-implimentation:
    type: cloudify.netconf.nodes.xml_rpc
    properties:
      netconf_auth:
        user: <user on device>
        password: <password on device, optional>
        ip: <ip for device>
        key_content: <private key content>
        port: <port for device, optional by default 830>
      metadata:
        xmlns:
          _: <default namespace>
        capabilities:
          <list of capabilities, optional>
    interfaces:
      cloudify.interfaces.lifecycle:
        create: // can be create / configure / start / stop / delete
          inputs:
            strict_check: <ignore not critical errors in xml, optional>
            deep_error_check: <look deeply for errors, optional by default false>
            template: <template file name or URL>
            params: <dict params for template, optional>
              some_param_name: some param name
```

_template_ input suppoorts single file location. It can be:
* a path which is resolverd as blueprint resource
* a URL

```

node_templates:
  some-implimentation:
    type: cloudify.netconf.nodes.xml_rpc
    properties:
      netconf_auth:
        user: <user on device>
        password: <password on device, optional>
        ip: <ip for device>
        key_content: <private key content>
        port: <port for device, optional by default 830>
      metadata:
        xmlns:
          _: <default namespace>
        capabilities:
          <list of capabilities, optional>
    interfaces:
      cloudify.interfaces.lifecycle:
        create: // can be create / configure / start / stop / delete
          inputs:
            strict_check: <ignore not critical errors in xml, optional>
            deep_error_check: <look deeply for errors, optional by default false>
            templates: [<template file name or URL>]
            params: <dict params for template, optional>
              some_param_name: some param name
```

_templates_ input may also be used instead of a single _template_. _templates_ does
not support multiple calls in one file - each call sould be provided as a
separete call.
The same ways of specifying file location as for template are supported:
blueprint resource or URL.

Notes:

* All content in metadata in common usage generated by yttc command, and
you can use output of such tool for 'parent/template' blueprint that can
be base of yours blueprint. Its not strictly needed but very useful
because you can use results of such tools as base for validate your
blueprint.
* You have examples for all basic operation of netconf protocol in
properties of base class of node (described in plugin.yaml) so you can
use all of such operation by `payload: { get_property: [ your_node, rfc6020@unlock ] }`.
* If you feel self as confidential person - you can write any structure
to payload without any validation by in yang. Sometime it will
be very useful for crazy devices without correct yang schemas.
* Also we have magic help functionality like `lock`, `back_database`,
`front_database`. So one by one: `lock` - we will lock database in list
for you before any operation and unlock after operations, its very useful
if you have several consumers that want to change configuration and
doesn't like to sync before change. `back_database`/`front_database` -
we can copy configuration from front database to back database before run
operations and all operations we will do in this database(if you don't
set any in rfc6020@target) and after will move your changes to front database.
Such functionality is useful for case when you want to have consistent
settings with apply after all changes. And sometime device does not
support change configuration in place.
* `save_to` - response from server will be saved to runtime node properties
files with such name and namespaces for this result will be saved to field
with same name and suffix `_ns`.
* We have copy of xslt/relaxng files from `pyang` in `share-files` and have
fully same license as original files from pyang.
* you can skip set `ip` in `netconf_auth` in case if your node have
`cloudify.nodes.Compute` node in relationships with type
`cloudify.relationships.contained_in`. In such case as `ip` will be used
`ip` from compute node.
* as value `ip` in `netconf_auth` can be list of `ip's` if you have failback.

## Versions:

Look to [ChangeLog](CHANGELOG.txt).
