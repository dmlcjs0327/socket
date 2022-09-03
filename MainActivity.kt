//출처: https://elecs.tistory.com/345

import android.content.Context
import android.net.ConnectivityManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.Message
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import kotlinx.android.synthetic.main.activity_main.*
import java.io.DataInputStream
import java.io.DataOutputStream
import java.net.*

class MainActivity : AppCompatActivity() {

    companion object{ //전역변수 
        var socket = Socket()
        var server = ServerSocket()
        
        lateinit var DataOutputSocket: DataOutputStream
        lateinit var DataInputSocket: DataInputStream
        lateinit var cManager: ConnectivityManager //인터넷 연결 여부 확인을 위한 변수

        var ip = "192.168.0.1"
        var port = 2222

        var mHandler = Handler() //
        var closed = false 
    }
    
    override fun onCreate(savedInstanceState: Bundle?) { //시작함수
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main) 

        cManager = applicationContext.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager //인터넷 연결 여부 확인
        server.close()
        socket.close()
        
        //button_connect를 눌렀을 때에 대한 동작
        button_connect.setOnClickListener { //클라이언트 -> 서버 접속 
        
            if(et_ip.text.isNotEmpty()) { //ip 입력창이 비어있지 않으면
                ip = et_ip.text.toString() //입력창의 ip를 저장

                if(et_port.text.isNotEmpty()) { //port 입력창이 비어있지 않으면
                    port = et_port.text.toString().toInt() //입력창의 port를 저장

                    if(port<0 || port>65535){//port범위가 비정상이면
                        Toast.makeText(this@MainActivity, "PORT 번호는 0부터 65535까지만 가능합니다.", Toast.LENGTH_SHORT).show() //경고문(토스트) 출력
                    }
                    else{//port범위가 정상이면
                        if(!socket.isClosed){ //소켓이 열려있으면
                            Toast.makeText(this@MainActivity, ip + "에 이미 연결되어 있습니다.", Toast.LENGTH_SHORT).show() //경고문(토스트) 출력
                        }
                        else { //소켓이 닫혀있으면
                            Connect().start() //연결을 위한 thread를 시작
                        }
                    } 
                }
                else{ //port 입력창이 비어있으면
                    Toast.makeText(this@MainActivity, "PORT 번호를 입력해주세요.", Toast.LENGTH_SHORT).show()
                } 
            }
            else{ //ip 입력창이 비어있으면
                Toast.makeText(this@MainActivity, "IP 주소를 입력해주세요.", Toast.LENGTH_SHORT).show() 
            }
        }

        //button_disconnect를 눌렀을 때에 대한 동작
        button_disconnect.setOnClickListener { //클라이언트 -> 서버 접속 끊기 
            if(!socket.isClosed){ //소켓이 열려있으면
                Disconnect().start() 
            }
            else{ //소켓이 닫혀있으면
                Toast.makeText(this@MainActivity, "서버와 연결이 되어있지 않습니다.", Toast.LENGTH_SHORT).show() 
            }
        } 
        
        //button_setserver를 눌렀을 때에 대한 동작
        button_setserver.setOnClickListener{ //서버 포트 열기 

            if(et_port.text.isNotEmpty()) {//port 입력창이 비어있지 않으면
                val cport = et_port.text.toString().toInt() //입력창의 port를 숫자로 변환하여 저장

                if(cport<0 || cport>65535){ //port범위가 비정상이면
                    Toast.makeText(this@MainActivity, "PORT 번호는 0부터 65535까지만 가능합니다.", Toast.LENGTH_SHORT).show()
                }
                else{ //port범위가 정상이면
                    if(server.isClosed) { //서버가 닫혀있으면
                        port = cport //포트를 갱신하고
                        SetServer().start() //서버 시작
                    }
                    else{ //서버가 열려있으면
                        Toast.makeText(this@MainActivity, port.toString() + "번 포트가 열려있습니다.", Toast.LENGTH_SHORT).show() 
                    }
                } 
            }
            else{//port 입력창이 비어있으면
                Toast.makeText(this@MainActivity, "PORT 번호를 입력해주세요.", Toast.LENGTH_SHORT).show() 
            }
        } 

        //button_closeserver를 눌렀을 때에 대한 동작
        button_closeserver.setOnClickListener { //서버 포트 닫기 
            if(!server.isClosed){//서버가 열려있으면
                CloseServer().start() 
            }
            else{//서버가 닫혀있으면
                mHandler.obtainMessage(17).apply { //토스트: 포트가 이미 닫혀있습니다.
                    sendToTarget()
                } 
            }
        } 
            
        //button_info를 눌렀을 때에 대한 동작
        button_info.setOnClickListener { //자기자신의 연결 정보(IP 주소)확인 
            ShowInfo().start()
        } 
        
        //button_msg를 눌렀을 때에 대한 동작
        button_msg.setOnClickListener { //상대에게 메시지 전송 
            if(socket.isClosed){ //소켓이 닫혀있으면
                Toast.makeText(this@MainActivity, "연결이 되어있지 않습니다.", Toast.LENGTH_SHORT).show() 
            }
            else { //소켓이 열려있으면
                val mThread = SendMessage()
                mThread.setMsg(et_msg.text.toString())
                mThread.start() 
            }
        } 

        //스레드 간 통신을 위한 handler 객체 선언
        mHandler = object : Handler(Looper.getMainLooper()){//Thread들로부터 Handler를 통해 메시지를 수신
            override fun handleMessage(msg: Message) {
                super.handleMessage(msg)
                when(msg.what){
                    1->Toast.makeText(this@MainActivity, "IP 주소가 잘못되었거나 서버의 포트가 개방되지 않았습니다.", Toast.LENGTH_SHORT).show() 
                    2->Toast.makeText(this@MainActivity, "서버 포트 "+port +"가 준비되었습니다.", Toast.LENGTH_SHORT).show() 
                    3->Toast.makeText(this@MainActivity, msg.obj.toString(), Toast.LENGTH_SHORT).show() 
                    4->Toast.makeText(this@MainActivity, "연결이 종료되었습니다.", Toast.LENGTH_SHORT).show() 
                    5->Toast.makeText(this@MainActivity, "이미 사용중인 포트입니다.", Toast.LENGTH_SHORT).show() 
                    6->Toast.makeText(this@MainActivity, "서버 준비에 실패하였습니다.", Toast.LENGTH_SHORT).show() 
                    7->Toast.makeText(this@MainActivity, "서버가 종료되었습니다.", Toast.LENGTH_SHORT).show() 
                    8->Toast.makeText(this@MainActivity, "서버가 정상적으로 닫히는데 실패하였습니다.", Toast.LENGTH_SHORT).show() 
                    9-> text_status.text = msg.obj as String 
                    11->Toast.makeText(this@MainActivity, "서버에 접속하였습니다.", Toast.LENGTH_SHORT).show() 
                    12->Toast.makeText(this@MainActivity, "메시지 전송에 실패하였습니다.", Toast.LENGTH_SHORT).show() 
                    13->Toast.makeText(this@MainActivity, "클라이언트와 연결되었습니다.",Toast.LENGTH_SHORT).show() 
                    14->Toast.makeText(this@MainActivity, "서버에서 응답이 없습니다.", Toast.LENGTH_SHORT).show()
                    15->Toast.makeText(this@MainActivity, "서버와의 연결을 종료합니다.", Toast.LENGTH_SHORT).show() 
                    16->Toast.makeText(this@MainActivity, "클라이언트와의 연결을 종료합니다.", Toast.LENGTH_SHORT).show() 
                    17->Toast.makeText(this@MainActivity, "포트가 이미 닫혀있습니다.", Toast.LENGTH_SHORT).show() 
                    18->Toast.makeText(this@MainActivity, "서버와의 연결이 끊어졌습니다.", Toast.LENGTH_SHORT).show()
                } 
            }
        } 
    }
    


    class Connect:Thread(){ 

        override fun run(){ 
            try{
                socket = Socket(ip, port) //소켓 생성

                DataOutputSocket = DataOutputStream(socket.getOutputStream())
                DataInputSocket = DataInputStream(socket.getInputStream())

                val b = DataInputSocket.read()

                if(b==1){ //서버로부터 접속이 확인되었을 때 
                    mHandler.obtainMessage(11).apply {
                        sendToTarget() 
                    } 
                    ClientSocket().start()
                }else{ //서버 접속에 성공하였으나 서버가 응답을 하지 않았을 때 
                    mHandler.obtainMessage(14).apply {
                        sendToTarget() 
                    } 
                    socket.close()
                } 
            }catch(e:Exception){ //연결 실패
                val state = 1
                mHandler.obtainMessage(state).apply { 
                    sendToTarget()
                }
                socket.close() 
            } 
        } 
    }
    
    class ClientSocket:Thread(){

        override fun run() { 
            try{
                while (true) { 
                    val ac = DataInputSocket.read() 
                    if(ac == 2) { //서버로부터 메시지 수신 명령을 받았을 때
                        val input = DataInputSocket.readUTF().toString().trim() 
                        val msg = mHandler.obtainMessage()
                        msg.what = 3
                        msg.obj = recvInput
                        mHandler.sendMessage(msg) 
                    }else if(ac == 10){ //서버로부터 접속 종료 명령을 받았을 때
                        mHandler.obtainMessage(18).apply { 
                            sendToTarget()
                        }
                        ocket.close()
                        break 
                    }
                } 
            }catch(e:SocketException){ //소켓이 닫혔을 때
                mHandler.obtainMessage(15).apply { 
                    sendToTarget()
                } 
            }
        } 
    }
    
    class Disconnect:Thread(){
        override fun run() { 
            try{
                DataOutputSocket.write(10) //서버에게 접속 종료 명령 전송
                socket.close() 
            }catch(e:Exception){}
        } 
    }
    
    class SetServer:Thread(){ 
        override fun run(){ 
            try{
                server = ServerSocket(port) //포트 개방
                mHandler.obtainMessage(2, "").apply { 
                    sendToTarget()
                } 
                while(true) { 
                    socket = server.accept() 
                    DataOutputSocket = DataOutputStream(socket.getOutputStream()) 
                    DataInputSocket = DataInputStream(socket.getInputStream())
                    DataOutputSocket.write(1) //클라이언트에게 서버의 소켓 생성을 알림 
                    mHandler.obtainMessage(13).apply {
                        sendToTarget()
                    } 
                    while (true) {
                        val ac = DataInputSocket.read()
                        if(ac==10){ //클라이언트로부터 소켓 종료 명령 수신 
                            mHandler.obtainMessage(16).apply {
                                sendToTarget() 
                            } 
                            break
                        }else if(ac == 2){ //클라이언트로부터 메시지 전송 명령 수신 
                            val bac = DataInputSocket.readUTF() 
                            val input = bac.toString() 
                            val recvInput = input.trim()
                            val msg = mHandler.obtainMessage() 
                            msg.what = 3 
                            msg.obj = recvInput 
                            mHandler.sendMessage(msg) //핸들러에게 클라이언트로 전달받은 메시지 전송
                        } 
                    }
                }
            }catch(e:BindException) { //이미 개방된 포트를 개방하려 시도하였을때
                mHandler.obtainMessage(5).apply { 
                    sendToTarget()
                } 
            }catch(e:SocketException){ //소켓이 닫혔을 때
                mHandler.obtainMessage(7).apply { 
                    sendToTarget()
                } 
            } 
            catch(e:Exception){
                if(!closed) {
                    mHandler.obtainMessage(6).apply {
                        sendToTarget() 
                    }
                }else{ 
                    closed = false
                } 
            }
        } 
    }
    
    class CloseServer:Thread(){
        override fun run(){ 
            try{
                closed = true
                DataOutputSocket.write(10) //클라이언트에게 서버가 종료되었음을 알림
                socket.close()
                server.close() 
            }catch(e:Exception){
                e.printStackTrace()
                mHandler.obtainMessage(8).apply { 
                    sendToTarget()
                } 
            }
        } 
    }
    
    class SendMessage:Thread(){
        private lateinit var msg:String
        
        fun setMsg(m:String){ 
            msg = m
        } 

        override fun run() { 
            try{
                DataOutputSocket.writeInt(2) //메시지 전송 명령 전송
                DataOutputSocket.writeUTF(msg) //메시지 내용
            }catch(e:Exception){
                e.printStackTrace()
                mHandler.obtainMessage(12).apply { 
                    sendToTarget()
                } 
            }
        } 
    }
    
    class ShowInfo:Thread(){ 
        override fun run(){ 
            lateinit var ip:String 
            var breakLoop = false 
            val en = NetworkInterface.getNetworkInterfaces() 
            while(en.hasMoreElements()){
                val intf = en.nextElement()
                val enumIpAddr = intf.inetAddresses
                while(enumIpAddr.hasMoreElements()){
                    val inetAddress = enumIpAddr.nextElement() 
                    if(!inetAddress.isLoopbackAddress && inetAddress is Inet4Address){
                        ip = inetAddress.hostAddress.toString()
                        breakLoop = true
                        break 
                    }
                }
                if(breakLoop){ 
                    break
                } 
            }
            val msg = mHandler.obtainMessage()
            msg.what = 9 
            msg.obj = ip 
            mHandler.sendMessage(msg)
        } 
    } 
}
