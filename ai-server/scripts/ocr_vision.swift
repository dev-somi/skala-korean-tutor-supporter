// macOS Vision으로 이미지의 글자를 읽어 JSON 한 줄씩 출력한다.
// 사용: OCR_LANGS=ja-JP,ko-KR ocr_vision <이미지 경로>...  (OCR_LANGS 기본값 ko-KR,en-US. 앞 언어를 우선한다)
// 출력: {"file": 경로, "lines": [{"text", "x", "y", "w", "h"}]}  (좌표는 0~1, 왼쪽 위 기준)
import Foundation
import Vision

let langs = (ProcessInfo.processInfo.environment["OCR_LANGS"] ?? "ko-KR,en-US").split(separator: ",").map(String.init)

for path in CommandLine.arguments.dropFirst() {
    let url = URL(fileURLWithPath: path)
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = langs
    request.usesLanguageCorrection = true

    let handler = VNImageRequestHandler(url: url)
    var lines: [[String: Any]] = []
    do {
        try handler.perform([request])
        for obs in request.results ?? [] {
            guard let top = obs.topCandidates(1).first else { continue }
            let b = obs.boundingBox  // 왼쪽 아래 기준 → 왼쪽 위 기준으로 바꾼다
            lines.append([
                "text": top.string,
                "x": b.minX, "y": 1 - b.maxY, "w": b.width, "h": b.height,
            ])
        }
    } catch {
        FileHandle.standardError.write("\(path): \(error)\n".data(using: .utf8)!)
    }
    let out: [String: Any] = ["file": path, "lines": lines]
    let data = try! JSONSerialization.data(withJSONObject: out)
    print(String(data: data, encoding: .utf8)!)
}
