DỰ ÁN GIỮA KỲ



PHÂN HỆ ĐÓNG HỌC PHÍ CỦA ỨNG DỤNG iBanking





Anh (chị) hiện thực ứng dụng mô phỏng phân hệ đóng học phí của ứng dụng iBanking. Hệ thống cho phép người dùng sử dụng số dư trong tài khoản để thanh toán toàn bộ khoản học phí của một sinh viên TDTU. Một người dùng có thể thanh toán học phí cho chính mình hoặc cho sinh viên khác.





1\. Đăng nhập và thông tin người dùng



Người dùng đăng nhập vào hệ thống bằng username và password. Không yêu cầu hiện thực chức năng đăng ký tài khoản mới.



Hệ thống cần quản lý tối thiểu các thông tin của người dùng:



\- Họ và tên;

\- Số điện thoại;

\- Địa chỉ email;

\- Số dư khả dụng;

\- Lịch sử các giao dịch đã thực hiện.



Sau khi đăng nhập thành công, người dùng có thể truy cập chức năng Thanh toán học phí.





2\. Tra cứu và thanh toán học phí



Màn hình thanh toán học phí gồm ba nhóm thông tin:



a. Người nộp tiền:



\- Họ và tên;

\- Số điện thoại;

\- Địa chỉ email.



Các thông tin trên được lấy tự động từ tài khoản đang đăng nhập và người dùng không được chỉnh sửa.



b. Thông tin học phí:



\- Mã số sinh viên (MSSV);

\- Họ và tên sinh viên;

\- Số tiền học phí cần thanh toán.



Sau khi người dùng nhập MSSV, hệ thống phải tự động tra cứu và hiển thị thông tin sinh viên cùng khoản học phí còn phải thanh toán. Hệ thống chỉ cho phép thanh toán toàn bộ khoản học phí, không thực hiện thanh toán một phần.



c. Thông tin thanh toán



\- Số dư khả dụng của người nộp tiền;

\- Số tiền cần thanh toán;

\- Các thỏa thuận và điều khoản của hệ thống.



Giao dịch chỉ được phép thực hiện khi khoản học phí tồn tại, chưa được thanh toán và số dư khả dụng của người nộp tiền lớn hơn hoặc bằng số tiền cần thanh toán.



Nút Xác nhận giao dịch chỉ khả dụng khi các thông tin cần thiết đã đầy đủ và hợp lệ.





3\. Xác thực giao dịch bằng OTP



Sau khi người dùng xác nhận giao dịch, hệ thống gửi một mã OTP qua email đến địa chỉ email của người nộp tiền.



Mỗi OTP phải:



\- Được gắn với một giao dịch cụ thể;

\- Không trùng với OTP đang có hiệu lực của giao dịch khác;

\- Có thời hạn hiệu lực tối đa 5 phút;

\- Chỉ được sử dụng thành công một lần.



Người dùng nhập OTP và thực hiện xác nhận lần cuối. Hệ thống chỉ tiếp tục xử lý giao dịch khi OTP hợp lệ và còn thời hạn.





4\. Xử lý giao dịch thành công



Sau khi OTP được xác thực, hệ thống phải thực hiện đầy đủ các thao tác:



\- Kiểm tra lại tính hợp lệ của giao dịch và số dư khả dụng;

\- Trừ số tiền tương ứng khỏi tài khoản người nộp tiền;

\- Cập nhật khoản học phí tương ứng thành đã thanh toán;

\- Lưu giao dịch vào lịch sử giao dịch của người dùng;

\- Gửi email xác nhận giao dịch thành công đến người nộp tiền;

\- Kết thúc giao dịch và hiển thị kết quả cho người dùng.





5\. Tính nhất quán của giao dịch



Do hệ thống liên quan đến giao dịch tài chính, việc xử lý phải đảm bảo tính nhất quán của dữ liệu (data consistency).



Hệ thống phải xử lý đúng ít nhất hai tình huống có thể xảy ra đồng thời:



\- Nhiều giao dịch trên cùng một tài khoản: khi một giao dịch đang thực hiện thanh toán, hệ thống phải ngăn việc các giao dịch đồng thời sử dụng cùng một số dư dẫn đến chi tiêu vượt quá số dư khả dụng.



\- Nhiều tài khoản thanh toán cùng một khoản học phí: nếu hai người dùng đồng thời thanh toán cho cùng một MSSV, hệ thống phải đảm bảo khoản học phí chỉ được thanh toán thành công một lần.



Sau khi giao dịch hoàn tất, số dư tài khoản, trạng thái học phí và lịch sử giao dịch phải phản ánh đúng kết quả cuối cùng.





Yêu cầu:



Dựa vào mô tả trên, anh (chị) tiến hành phân tích, thiết kế và hiện thực phân hệ đóng học phí, đáp ứng các yêu cầu sau:



1\. Phân tích nghiệp vụ và dữ liệu của phân hệ; mô tả kết quả phân tích bằng các lược đồ phù hợp, tối thiểu gồm Use Case Diagram và Entity Relationship Diagram (ERD).



2\. Thiết kế kiến trúc Microservices cho phân hệ; xác định service, trách nhiệm của từng service và cách thức giao tiếp giữa các service. Trình bày thiết kế bằng Microservices Architecture Diagram.



3\. Thiết kế REST API cho các chức năng của phân hệ; xác định URI, HTTP Method, Input/Request, Output/Response và HTTP Status Code của các API.



4\. Thiết kế và hiện thực cơ sở dữ liệu của phân hệ bằng SQL và/hoặc NoSQL phù hợp.



5\. Lập trình các service và API để thực hiện được đầy đủ luồng nghiệp vụ được mô tả.



6\. Hiện thực cơ chế xử lý transaction và concurrency, đảm bảo tính nhất quán của dữ liệu trong các tình huống giao dịch đồng thời được mô tả.



7\. Lập trình giao diện tương tác người dùng, ưu tiên Web Application, và tích hợp với các API đã xây dựng.



8\. Chuẩn bị tài liệu và trình diễn sản phẩm, bao gồm hướng dẫn cài đặt, khởi chạy và sử dụng hệ thống.



PROJECT-SPECIFIC DECISION



Although the original assignment states that a user may pay tuition for themselves or another student, this project implementation intentionally restricts the payment scope to self-payment only.



The authenticated user is identified by the uid contained in the JWT.



The payer information must be loaded automatically through:



GET /payers/me



The tuition information must be loaded for the authenticated user through:



GET /tuition/me



The client must NOT be allowed to provide or modify payer\_uid, uid, student\_id, MSSV, or any other identifier to select another payer/student for payment.



The system must ensure:



JWT uid

&#x20;   ↓

Authenticated User

&#x20;   ↓

Payer

&#x20;   ↓

Own Student / Tuition

&#x20;   ↓

Payment



Therefore, a logged-in user cannot use their account balance to pay tuition for another student.



All payer information displayed on the payment screen must be read-only and loaded from the authenticated account.

