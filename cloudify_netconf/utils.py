# Copyright (c) 2015-2019 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from lxml import etree
from collections import OrderedDict

from cloudify import exceptions as cfy_exc


NETCONF_NAMESPACE = "urn:ietf:params:xml:ns:netconf:base:1.0"

# default netconf namespace short name
DEFAULT_NCNS = "rfc6020"


def _node_name(name, namespace, xmlns):
    attibute = False
    tag_namespace = namespace
    if "@" in name:
        spilted_names = name.split("@")
        if len(spilted_names) == 2:
            # tag with namespace
            tag_namespace = spilted_names[0]
            name = spilted_names[1]
        else:
            if len(spilted_names) == 3 and spilted_names[0] == '_':
                # attibute with namespace
                tag_namespace = spilted_names[1]
                name = spilted_names[2]
                attibute = True
            else:
                # i dont know what is it
                raise cfy_exc.NonRecoverableError(
                    "wrong format of xml element name"
                )
    # looks as empty namespace
    if tag_namespace == "":
        tag_namespace = namespace
    # replace to real ns
    if tag_namespace in xmlns:
        # we can use such namespace
        return attibute, tag_namespace, "{%s}%s" % (xmlns[tag_namespace], name)
    else:
        # we dont have such namespace
        return attibute, tag_namespace, name


def _general_node(parent, node_name, value, xmlns, namespace, nsmap):
    # harcoded magic value for case when we need set attributes to some tag
    # with text value inside
    if node_name == "_@@":
        parent.text = str(value)
        return
    # special case for raw nodes
    if node_name == "_!_":
        parent.append(etree.XML(value))
        return
    # general logic
    attribute, tag_namespace, tag_name = _node_name(
        node_name, namespace, xmlns
    )
    # attibute can't contain complicated values, ignore attribute flag
    # for now
    if not attribute or isinstance(value, dict):
        # can be separate node
        result = etree.Element(
            tag_name, nsmap=nsmap
        )
        if isinstance(value, dict):
            _gen_xml(result, value, xmlns, tag_namespace, nsmap)
        else:
            if value is not None:
                # dont add None value
                result.text = str(value)
        parent.append(result)
    else:
        # attibute
        parent.attrib[tag_name] = str(value)


def _gen_xml(parent, properties, xmlns, namespace, nsmap):
    for node in properties.keys():
        if isinstance(properties[node], list):
            # will be many nodes with same name
            for value in properties[node]:
                _general_node(
                    parent, node, value, xmlns, namespace, nsmap
                )
        else:
            _general_node(
                parent, node, properties[node], xmlns, namespace, nsmap
            )


def update_xmlns(xmlns):
    netconf_namespace = DEFAULT_NCNS
    for k in xmlns:
        if xmlns[k] == NETCONF_NAMESPACE:
            netconf_namespace = k
            break
    if netconf_namespace not in xmlns:
        xmlns[netconf_namespace] = NETCONF_NAMESPACE
    return netconf_namespace, xmlns


def create_nsmap(xmlns):
    netconf_namespace, xmlns = update_xmlns(xmlns)
    nsmap = {}
    for k in xmlns:
        if k != "_":
            nsmap[k] = xmlns[k]
        else:
            nsmap[None] = xmlns[k]
    return nsmap, netconf_namespace, xmlns


def generate_xml_node(model, xmlns, parent_tag):
    if not xmlns:
        raise cfy_exc.NonRecoverableError(
            "node doesn't have any namespaces"
        )
    nsmap, netconf_namespace, xmlns = create_nsmap(xmlns)
    # we does not support attibutes on top level,
    # so for now ignore attibute flag
    _, _, tag_name = _node_name(parent_tag, netconf_namespace, xmlns)
    parent = etree.Element(
        tag_name, nsmap=nsmap
    )
    _gen_xml(parent, model, xmlns, '_', nsmap)
    return parent


def rpc_gen(message_id, operation, netconf_namespace, data, xmlns):
    if "@" in operation:
        action_name = operation
    else:
        action_name = netconf_namespace + "@" + operation
    new_node = {
        action_name: data,
        "_@" + netconf_namespace + "@message-id": message_id
    }
    return generate_xml_node(
        new_node,
        xmlns,
        'rpc'
    )


def _get_free_ns(xmlns, namespace, prefered_ns=None):
    """search some not existed namespace name, ands save namespace"""
    # search maybe we have some cool name for it
    namespace_name = None
    if prefered_ns:
        for ns in prefered_ns:
            if ns is not None and prefered_ns[ns] == namespace:
                # we have some short and cool name
                namespace_name = ns
                break
    # we dont have cool names, create ugly
    if not namespace_name:
        namespace_name = "_" + namespace.replace(":", "_")
        namespace_name = namespace_name.replace("/", "_")
    # save uniq for namespace name
    while namespace_name in xmlns:
        namespace_name = "_" + namespace_name + "_"
    xmlns[namespace_name] = namespace
    return namespace_name


def _short_names(name, xmlns, nsmap=None):
    if name[0] != "{":
        return name
    for ns_short in xmlns:
        fullnamespace = "{" + xmlns[ns_short] + "}"
        if fullnamespace in name:
            if not ns_short or ns_short == '_':
                return name.replace(fullnamespace, "")
            else:
                return name.replace(fullnamespace, ns_short + "@")
    # we dont have such namespace,
    # in any case we will have } in string if we have used lxml
    namespace = name[1:]
    name = namespace[namespace.find("}") + 1:]
    namespace = namespace[:namespace.find("}")]
    return _get_free_ns(xmlns, namespace, nsmap) + "@" + name


def _node_to_dict(parent_list, xml_node, xmlns):
    if isinstance(xml_node, etree._Comment):
        return

    name = _short_names(xml_node.tag, xmlns, xml_node.nsmap)
    if not xml_node.getchildren() and not xml_node.attrib:
        # we dont support text inside of node
        # if we have subnodes or attibutes
        value = xml_node.text
    else:
        value_list = []
        if xml_node.text and len(xml_node.text.strip()):
            value_list.append(("_@@", xml_node.text.strip()))
        for i in xml_node.getchildren():
            _node_to_dict(value_list, i, xmlns)
        for k in xml_node.attrib:
            k_short = _short_names(k, xmlns, xml_node.nsmap)
            if '@' in k_short:
                # already have namespace
                k_short = "_@" + k_short
            else:
                # we dont have namespace yet
                k_short = "_@@" + k_short
            value_list.append((k_short, xml_node.attrib[k]))
        value = OrderedDict(value_list)
    for i in range(len(parent_list)):
        (k, previous) = parent_list[i]
        if k == name:
            if isinstance(previous, list):
                previous.append(value)
            else:
                parent_list[i] = (name, [previous, value])
            break
    else:
        parent_list.append((name, value))


def generate_dict_node(xml_node, nslist):
    netconf_namespace, xmlns = update_xmlns(nslist)
    parent_list = []
    _node_to_dict(parent_list, xml_node, xmlns)
    return OrderedDict(parent_list)


def default_xmlns():
    """default namespace list for relaxng"""
    return {
        '_': NETCONF_NAMESPACE,
    }
