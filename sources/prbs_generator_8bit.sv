`timescale 1ns/1ns

module prbs_generator_8bit (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        enable,
    input  wire [2:0]  prbs_type,
    output wire  [7:0]  prbs_out,
    input  wire [31:0] seed,
    input  wire        load
);

    reg [31:0] prbs_out_pre;
    reg        load_d;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            prbs_out_pre <= 32'd0;
            load_d <= 1'b0;
        end
        else begin
            load_d <= load;

            if (load && !load_d) begin
                prbs_out_pre <= seed;
            end
            else if (enable) begin
                case (prbs_type)
                    3'd0: begin
                        prbs_out_pre <= {prbs_out_pre[23:0], prbs_out_pre[5:1] ^ prbs_out_pre[4:0], prbs_out_pre[6] ^ prbs_out_pre[5] ^ prbs_out_pre[0], prbs_out_pre[6] ^ prbs_out_pre[4], prbs_out_pre[5] ^ prbs_out_pre[3]};
                    end
                    3'd1: begin
                        prbs_out_pre <= {prbs_out_pre[23:0], prbs_out_pre[14:7] ^ prbs_out_pre[13:6]};
                    end
                    3'd2: begin
                        prbs_out_pre <= {prbs_out_pre[23:0], prbs_out_pre[22:15] ^ prbs_out_pre[17:10]};
                    end
                    3'd3: begin
                        prbs_out_pre <= {prbs_out_pre[23:0], prbs_out_pre[30:23] ^ prbs_out_pre[27:20]};
                    end
                    default: begin
                        prbs_out_pre <= prbs_out_pre;
                    end
                endcase
            end
        end
    end

    assign prbs_out = prbs_out_pre[7:0];
endmodule
