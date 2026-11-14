import XCTest
@testable import JarvisCore

/// The wire format for choosing several worker models and for seeing how a long file is split (the same JSON the Python bridge sends and reads).
final class CrewSplitTests: XCTestCase {
    func testRequestCarriesTheSwitchedOnModelsAndFileSizes() throws {
        let req = CrewRequest(task: "t", boss: "ol|boss:8b", workerModels: ["ol|a:1b", "ol|b:3b"],
                              inputs: [.init(name: "big.pdf", kind: "pdf", text: "", chars: 180_000, pages: 90)])
        let obj = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(req)) as? [String: Any])
        XCTAssertEqual(obj["worker_models"] as? [String], ["ol|a:1b", "ol|b:3b"])
        let input = try XCTUnwrap((obj["inputs"] as? [[String: Any]])?.first)
        XCTAssertEqual(input["chars"] as? Int, 180_000); XCTAssertEqual(input["pages"] as? Int, 90)
        let plain = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(CrewRequest(task: "t", boss: "b"))) as? [String: Any])
        XCTAssertEqual(plain["worker_models"] as? [String], [])           // automatic
    }

    func testPreviewDecodesTheSplitAndWhichModelReadsWhat() throws {
        let json = #"""
        {"plan":{"feasible":true,"mode":"parallel","label":"x","max_workers":3,"budget":1,"boss_bytes":1,"worker_bytes":1,"reason":"ok","warnings":[]},"boss":"ol|boss:8b","workers":[],
         "layout":{"parts":[{"name":"big.pdf (pages 1-30)","parent":"big.pdf","label":"pages 1-30","model":"ol|a:1b","chars":60000},
                            {"name":"big.pdf (pages 31-90)","parent":"big.pdf","label":"pages 31-90","model":null,"chars":120000}],
                   "split":[{"name":"big.pdf","pages":90,"chars":180000,"parts":["pages 1-30","pages 31-90"]}],"unused":["ol|c:7b"]}}
        """#
        let d = JSONDecoder(); d.keyDecodingStrategy = .convertFromSnakeCase
        let p = try d.decode(CrewPreview.self, from: Data(json.utf8))
        let l = try XCTUnwrap(p.layout)
        XCTAssertEqual(l.parts.count, 2); XCTAssertEqual(l.parts[0].model, "ol|a:1b"); XCTAssertNil(l.parts[1].model)
        XCTAssertEqual(l.split.first?.pages, 90); XCTAssertEqual(l.unused, ["ol|c:7b"])
        // an older bridge sends no layout: still decodes
        let old = try d.decode(CrewPreview.self, from: Data(#"{"plan":{"feasible":true,"mode":"swap","label":"x","max_workers":1,"budget":1,"boss_bytes":1,"worker_bytes":1,"reason":"","warnings":[]},"boss":"b","workers":[]}"#.utf8))
        XCTAssertNil(old.layout)
    }
}
